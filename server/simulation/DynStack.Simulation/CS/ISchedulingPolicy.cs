using DynStack.DataModel.CS;

namespace DynStack.Simulation.CS {
  /// <summary>
  /// External scheduling policy called synchronously at each simulation tick.
  /// Used in sync mode so the simulation waits for the policy before advancing time.
  /// </summary>
  public interface ISchedulingPolicy {
    CraneSchedulingSolution GetSolution(World world);
  }
}
