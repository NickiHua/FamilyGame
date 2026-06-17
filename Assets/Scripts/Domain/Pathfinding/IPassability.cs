using System;
using FantacyCentry.Domain.Grid;

namespace FantacyCentry.Domain.Pathfinding
{
    /// <summary>
    /// Decides whether a unit may ENTER or STOP on a cell during movement. Lets the pathfinder
    /// stay decoupled from BattleState: callers supply occupancy rules (e.g. block enemies,
    /// pass through allies but don't stop on them).
    /// </summary>
    public interface IPassability
    {
        /// <summary>Can the moving unit pass THROUGH this cell (terrain walkable + not blocked by a foe)?</summary>
        bool CanEnter(GridPos cell);

        /// <summary>Can the moving unit STOP here (passable AND not occupied by anyone)?</summary>
        bool CanStop(GridPos cell);

        /// <summary>Movement-point cost to enter the cell (terrain-based).</summary>
        int EnterCost(GridPos cell);
    }

    /// <summary>
    /// Default passability driven by the map plus an occupancy lookup. Enemies block movement
    /// entirely; allied units can be passed through but not stopped on (standard SRPG rule).
    /// </summary>
    public sealed class MapPassability : IPassability
    {
        private readonly BattleMap _map;
        private readonly Func<GridPos, Units.Team?> _occupantTeam; // null = empty
        private readonly Units.Team _moverTeam;

        public MapPassability(BattleMap map, Units.Team moverTeam, Func<GridPos, Units.Team?> occupantTeam)
        {
            _map = map;
            _moverTeam = moverTeam;
            _occupantTeam = occupantTeam;
        }

        private static bool IsFoe(Units.Team mover, Units.Team other)
            => (mover == Units.Team.Enemy) != (other == Units.Team.Enemy);

        public bool CanEnter(GridPos cell)
        {
            if (!_map.IsWalkable(cell)) return false;
            Units.Team? occ = _occupantTeam(cell);
            return !occ.HasValue || !IsFoe(_moverTeam, occ.Value); // can pass allies, not foes
        }

        public bool CanStop(GridPos cell)
            => _map.IsWalkable(cell) && !_occupantTeam(cell).HasValue;

        public int EnterCost(GridPos cell) => _map.MoveCost(cell);
    }
}
