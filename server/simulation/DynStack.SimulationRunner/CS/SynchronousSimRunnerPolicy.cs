using DynStack.DataModel.CS;
using DynStack.Simulation.CS;
using NetMQ;
using NetMQ.Sockets;
using ProtoBuf;
using System;
using System.IO;
using System.Text;

namespace DynStack.SimulationRunner.CS {
  /// <summary>
  /// Bridges the CS simulation to an external Python (or any language) solver
  /// over ZMQ in synchronous mode. The simulation blocks at each tick waiting
  /// for the solver to respond before advancing simulated time.
  /// </summary>
  public class SynchronousSimRunnerPolicy : ISchedulingPolicy, IDisposable {
    private readonly INetMQSocket socket;
    private bool established = false;

    public SynchronousSimRunnerPolicy(string url, string id) {
      socket = new DealerSocket();
      socket.Options.Identity = Encoding.UTF8.GetBytes(id);
      // Give Dispose a moment to flush the trailing "done" frame (see
      // SendCompleted). Default linger can drop a just-queued send.
      socket.Options.Linger = TimeSpan.FromSeconds(1);
      socket.Bind(url);
    }

    public void Dispose() {
      if (!socket.IsDisposed)
        socket.Dispose();
    }

    /// <summary>
    /// LOCAL-ONLY end-of-run signal. Sends a ["", "done"] frame so a sync
    /// client can stop immediately instead of waiting out its receive
    /// timeout. Upstream/competition servers never send this; the client
    /// still treats receive-silence as end-of-run, so this is purely a
    /// local training speedup and is safe to omit. See LOCAL_CHANGES.md.
    /// </summary>
    public void SendCompleted() {
      if (socket.IsDisposed) return;
      socket.SendFrameEmpty(more: true);
      socket.SendFrame("done", more: false);
    }

    public CraneSchedulingSolution GetSolution(World world) {
      using var worldStream = new MemoryStream();
      Serializer.Serialize(worldStream, world);
      var bytes = worldStream.ToArray();

      // LOCAL-ONLY first-contact fix (see LOCAL_CHANGES.md). A DEALER client
      // that has just connected can miss the very first 'world' frame (its
      // receive pipe isn't wired up yet). With the original 5 s receive
      // timeout that stalled the first tick of EVERY run by ~5 s. Until the
      // first reply lands we resend on a short 200 ms cadence (still blocking
      // up to a generous deadline, so a slow-booting client is awaited and the
      // sim never advances without it). Once contact is established we revert
      // to the original 5 s / 3-strike behaviour, so a momentarily slow client
      // under parallel load is never spuriously resent (which could desync).
      var attemptTimeout = established
        ? TimeSpan.FromSeconds(5)
        : TimeSpan.FromMilliseconds(200);
      var firstContactDeadline = DateTime.UtcNow + TimeSpan.FromSeconds(30);
      int retriesLeft = 3;

      while (true) {
        socket.SendFrameEmpty(more: true);
        socket.SendFrame("world", more: true);
        socket.SendFrame(bytes, more: false);

        var answer = new NetMQMessage();
        if (socket.TryReceiveMultipartMessage(attemptTimeout, ref answer)) {
          answer.Pop(); // empty delimiter frame
          if (answer.Pop().ConvertToString() == "crane") {
            established = true;
            var payload = answer.Pop();
            if (payload.BufferSize == 0) return null;
            using var stream = new MemoryStream(payload.Buffer);
            return Serializer.Deserialize<CraneSchedulingSolution>(stream);
          }
        } else if (established) {
          if (--retriesLeft <= 0) {
            Console.WriteLine("[sync] No retries left, returning null");
            return null;
          }
        } else if (DateTime.UtcNow >= firstContactDeadline) {
          Console.WriteLine("[sync] client never connected, returning null");
          return null;
        }
      }
    }
  }
}
