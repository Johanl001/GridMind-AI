import pandas as pd
import numpy as np
import uuid
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from scipy.optimize import milp
from scipy.sparse import csr_matrix

from app.persistence.database import get_db_connection
from app.core.config import settings
from app.services.data_service import DataService
from app.services.forecasting_service import ForecastingService


class OptimizationService:
    def __init__(self):
        self.data_service = DataService()
        self.forecasting_service = ForecastingService()

    def _parse_time_string(self, time_str: str) -> float:
        """Convert HH:MM format to hours as float"""
        try:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            return float(hours + minutes / 60.0)
        except Exception:
            return 0.0

    def _get_tariff_rate(self, hour: int, tariff_schedule: List[Dict[str, Any]]) -> float:
        hour_of_day = int(hour) % 24
        for period in tariff_schedule:
            start_h = period.get('start_hour', 0)
            end_h = period.get('end_hour', 24)
            if start_h <= hour_of_day < end_h:
                return float(period.get('rate_per_kwh', 0.15))
        return 0.15

    def _calculate_cost(
        self,
        demand: List[float],
        tariff_schedule: List[Dict[str, Any]]
    ) -> float:
        total_cost = 0.0
        for h, consumption_kw in enumerate(demand):
            rate = self._get_tariff_rate(h, tariff_schedule)
            total_cost += float(consumption_kw) * rate
        return round(float(total_cost), 2)

    def _create_baseline_schedule(
        self,
        flexible_loads: List[Dict[str, Any]],
        horizon_hours: int,
        base_demand: List[float],
        tariff_schedule: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        schedule = []
        demand = list(base_demand[:horizon_hours]) if len(base_demand) >= horizon_hours else list(base_demand) + [0.0] * (horizon_hours - len(base_demand))

        for load in flexible_loads:
            start_h = int(np.floor(self._parse_time_string(load.get('earliest_start', '00:00'))))
            duration = max(1, int(round(load.get('duration_hours', 1))))
            power_kw = float(load.get('power_kw', 10.0))

            # Constrain within horizon
            start_idx = min(start_h, max(0, horizon_hours - duration))
            end_idx = min(start_idx + duration, horizon_hours)

            for h in range(start_idx, end_idx):
                rate = self._get_tariff_rate(h, tariff_schedule)
                schedule.append({
                    'load_id': str(load.get('id', '')),
                    'load_name': str(load.get('name', 'Load')),
                    'start_time': f"{h:02d}:00",
                    'end_time': f"{(h + 1):02d}:00",
                    'power_kw': round(power_kw, 2),
                    'energy_kwh': round(power_kw, 2),
                    'cost': round(power_kw * rate, 2)
                })
                demand[h] += power_kw

        return schedule, demand

    def _solve_milp(
        self,
        flexible_loads: List[Dict[str, Any]],
        base_demand: List[float],
        tariff_schedule: List[Dict[str, Any]],
        horizon_hours: int,
        weight_cost: float,
        weight_peak: float
    ) -> Tuple[List[Dict[str, Any]], List[float], List[str]]:
        n_loads = len(flexible_loads)
        max_time_slots = int(horizon_hours)
        n_vars = n_loads * max_time_slots

        c = np.zeros(n_vars)
        base_max = max(base_demand) if base_demand else 1.0

        for l, load in enumerate(flexible_loads):
            power_kw = float(load.get('power_kw', 10.0))
            duration = max(1, int(round(load.get('duration_hours', 1))))
            earliest_start = self._parse_time_string(load.get('earliest_start', '00:00'))
            latest_end = self._parse_time_string(load.get('latest_end', '24:00'))
            if latest_end <= earliest_start:
                latest_end = 24.0

            for t in range(max_time_slots):
                var_idx = l * max_time_slots + t
                start_time = t
                end_time = t + duration

                if end_time > horizon_hours or start_time < earliest_start or end_time > latest_end:
                    c[var_idx] = 1e6
                    continue

                cost_impact = 0.0
                peak_impact = 0.0
                for h in range(start_time, end_time):
                    rate = self._get_tariff_rate(h, tariff_schedule)
                    cost_impact += power_kw * rate
                    current_h_demand = base_demand[h] if h < len(base_demand) else 0.0
                    peak_impact += (current_h_demand + power_kw) / max(1.0, base_max)

                c[var_idx] = (weight_cost * cost_impact) + (weight_peak * peak_impact * 10.0)

        A_eq = []
        b_eq = []
        for l in range(n_loads):
            row = np.zeros(n_vars)
            for t in range(max_time_slots):
                row[l * max_time_slots + t] = 1.0
            A_eq.append(row)
            b_eq.append(1.0)

        bounds = [(0, 1) for _ in range(n_vars)]
        integrality = np.ones(n_vars)

        try:
            constraints = [{'A': csr_matrix(np.array(A_eq)), 'b': b_eq, 'equal': True}] if A_eq else []
            res = milp(c=c, constraints=constraints, bounds=bounds, integrality=integrality)

            if res.success:
                schedule = []
                demand = list(base_demand[:horizon_hours])
                for l, load in enumerate(flexible_loads):
                    power_kw = float(load.get('power_kw', 10.0))
                    duration = max(1, int(round(load.get('duration_hours', 1))))
                    for t in range(max_time_slots):
                        var_idx = l * max_time_slots + t
                        if res.x[var_idx] > 0.5:
                            for h in range(t, min(t + duration, horizon_hours)):
                                rate = self._get_tariff_rate(h, tariff_schedule)
                                schedule.append({
                                    'load_id': str(load.get('id', '')),
                                    'load_name': str(load.get('name', 'Load')),
                                    'start_time': f"{h:02d}:00",
                                    'end_time': f"{(h + 1):02d}:00",
                                    'power_kw': round(power_kw, 2),
                                    'energy_kwh': round(power_kw, 2),
                                    'cost': round(power_kw * rate, 2)
                                })
                                demand[h] += power_kw
                            break
                return schedule, demand, []
            else:
                return self._solve_heuristic(flexible_loads, base_demand, tariff_schedule, horizon_hours, weight_cost, weight_peak)
        except Exception:
            return self._solve_heuristic(flexible_loads, base_demand, tariff_schedule, horizon_hours, weight_cost, weight_peak)

    def _solve_heuristic(
        self,
        flexible_loads: List[Dict[str, Any]],
        base_demand: List[float],
        tariff_schedule: List[Dict[str, Any]],
        horizon_hours: int,
        weight_cost: float,
        weight_peak: float
    ) -> Tuple[List[Dict[str, Any]], List[float], List[str]]:
        demand = list(base_demand[:horizon_hours])
        schedule = []
        violations = []

        # Sort loads by power * duration descending (place heaviest loads first into deepest valleys)
        sorted_loads = sorted(
            flexible_loads,
            key=lambda l: float(l.get('power_kw', 10.0)) * float(l.get('duration_hours', 1.0)),
            reverse=True
        )

        for load in sorted_loads:
            power_kw = float(load.get('power_kw', 10.0))
            duration = max(1, int(round(load.get('duration_hours', 1.0))))
            earliest_start = int(np.floor(self._parse_time_string(load.get('earliest_start', '00:00'))))
            latest_end = int(np.ceil(self._parse_time_string(load.get('latest_end', '24:00'))))
            if latest_end <= earliest_start:
                latest_end = min(24, horizon_hours)

            valid_starts = []
            for t in range(earliest_start, min(latest_end - duration + 1, horizon_hours - duration + 1)):
                # Evaluate objective impact of starting at t
                cand_cost = sum(power_kw * self._get_tariff_rate(h, tariff_schedule) for h in range(t, t + duration))
                cand_peak = max(demand[h] + power_kw for h in range(t, t + duration))
                score = (weight_cost * cand_cost) + (weight_peak * cand_peak * 15.0)
                valid_starts.append((score, t))

            if not valid_starts:
                # If constraints too tight, fallback to earliest_start
                best_start = min(earliest_start, max(0, horizon_hours - duration))
                violations.append(f"Load '{load.get('name')}' time window relaxed to prevent infeasibility.")
            else:
                valid_starts.sort(key=lambda x: x[0])
                best_start = valid_starts[0][1]

            for h in range(best_start, min(best_start + duration, horizon_hours)):
                rate = self._get_tariff_rate(h, tariff_schedule)
                schedule.append({
                    'load_id': str(load.get('id', '')),
                    'load_name': str(load.get('name', 'Load')),
                    'start_time': f"{h:02d}:00",
                    'end_time': f"{(h + 1):02d}:00",
                    'power_kw': round(power_kw, 2),
                    'energy_kwh': round(power_kw, 2),
                    'cost': round(power_kw * rate, 2)
                })
                demand[h] += power_kw

        return schedule, demand, violations

    def _solve_priority(
        self,
        flexible_loads: List[Dict[str, Any]],
        base_demand: List[float],
        tariff_schedule: List[Dict[str, Any]],
        horizon_hours: int,
        weight_cost: float,
        weight_peak: float
    ) -> Tuple[List[Dict[str, Any]], List[float], List[str]]:
        # Priority order: lowest priority number = highest priority dispatch
        priority_sorted = sorted(flexible_loads, key=lambda l: int(l.get('priority', 1)))
        return self._solve_heuristic(priority_sorted, base_demand, tariff_schedule, horizon_hours, weight_cost, weight_peak)

    def run_optimization(
        self,
        dataset_id: str,
        forecast_id: Optional[str] = None,
        flexible_loads: Optional[List[Dict[str, Any]]] = None,
        tariff_schedule: Optional[List[Dict[str, Any]]] = None,
        horizon_hours: int = 24,
        weight_cost: float = 0.7,
        weight_peak: float = 0.3,
        solver: str = "milp"
    ) -> Dict[str, Any]:
        if flexible_loads is None:
            flexible_loads = []
        if tariff_schedule is None:
            tariff_schedule = []

        # Get baseline raw demand
        if forecast_id:
            forecast = self.forecasting_service.get_forecast(forecast_id)
            if not forecast:
                raise ValueError(f"Forecast {forecast_id} not found")
            raw_demand = [p['predicted_consumption'] for p in forecast['predictions']]
        else:
            filepath = self.data_service.data_dir / f"{dataset_id}.csv"
            if not filepath.exists():
                raise FileNotFoundError(f"Dataset {dataset_id} file not found")
            df = pd.read_csv(filepath)
            df = df.sort_values('timestamp')
            consumption = df['consumption_kwh'].values
            if len(consumption) >= horizon_hours:
                raw_demand = consumption[:horizon_hours].tolist()
            else:
                repeats = (horizon_hours // max(1, len(consumption))) + 1
                raw_demand = np.tile(consumption, repeats)[:horizon_hours].tolist()

        raw_demand = [float(d) for d in raw_demand[:horizon_hours]]
        if len(raw_demand) < horizon_hours:
            raw_demand.extend([raw_demand[-1] if raw_demand else 10.0] * (horizon_hours - len(raw_demand)))

        # Create baseline schedule where flexible loads run at default earliest times
        baseline_schedule, baseline_total_demand = self._create_baseline_schedule(
            flexible_loads, horizon_hours, raw_demand, tariff_schedule
        )

        solver_choice = solver.lower() if solver else "milp"
        if solver_choice == "heuristic":
            optimized_schedule, optimized_total_demand, violations = self._solve_heuristic(
                flexible_loads, raw_demand, tariff_schedule, horizon_hours, weight_cost, weight_peak
            )
        elif solver_choice == "priority":
            optimized_schedule, optimized_total_demand, violations = self._solve_priority(
                flexible_loads, raw_demand, tariff_schedule, horizon_hours, weight_cost, weight_peak
            )
        else:
            optimized_schedule, optimized_total_demand, violations = self._solve_milp(
                flexible_loads, raw_demand, tariff_schedule, horizon_hours, weight_cost, weight_peak
            )

        baseline_cost = self._calculate_cost(baseline_total_demand, tariff_schedule)
        optimized_cost = self._calculate_cost(optimized_total_demand, tariff_schedule)

        baseline_peak = round(float(max(baseline_total_demand)), 2) if baseline_total_demand else 0.0
        optimized_peak = round(float(max(optimized_total_demand)), 2) if optimized_total_demand else 0.0

        cost_savings = round(baseline_cost - optimized_cost, 2)
        cost_savings_pct = round((cost_savings / baseline_cost * 100), 2) if baseline_cost > 0 else 0.0
        peak_reduction = round(baseline_peak - optimized_peak, 2)
        peak_reduction_pct = round((peak_reduction / baseline_peak * 100), 2) if baseline_peak > 0 else 0.0

        # Format demand for charting (timestamps matching UI expectations)
        now = datetime.now()
        base_demand_formatted = [
            {
                'timestamp': (now + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00:00"),
                'demand_kw': round(float(val), 2)
            }
            for h, val in enumerate(baseline_total_demand)
        ]
        opt_demand_formatted = [
            {
                'timestamp': (now + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00:00"),
                'demand_kw': round(float(val), 2)
            }
            for h, val in enumerate(optimized_total_demand)
        ]

        optimization_id = str(uuid.uuid4())
        gen_time = datetime.now().isoformat()

        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO optimizations (
                    id, dataset_id, forecast_id, flexible_loads, tariff_schedule,
                    horizon_hours, weight_cost, weight_peak, baseline_schedule,
                    optimized_schedule, baseline_demand, optimized_demand,
                    baseline_cost, optimized_cost, cost_savings, cost_savings_pct,
                    baseline_peak, optimized_peak, peak_reduction, peak_reduction_pct,
                    constraint_violations, solver, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                optimization_id,
                dataset_id,
                forecast_id,
                json.dumps(flexible_loads),
                json.dumps(tariff_schedule),
                horizon_hours,
                weight_cost,
                weight_peak,
                json.dumps(baseline_schedule),
                json.dumps(optimized_schedule),
                json.dumps(base_demand_formatted),
                json.dumps(opt_demand_formatted),
                baseline_cost,
                optimized_cost,
                cost_savings,
                cost_savings_pct,
                baseline_peak,
                optimized_peak,
                peak_reduction,
                peak_reduction_pct,
                json.dumps(violations),
                solver_choice,
                gen_time
            ))
            conn.commit()

        return {
            'optimization_id': optimization_id,
            'dataset_id': dataset_id,
            'forecast_id': forecast_id,
            'flexible_loads': flexible_loads,
            'tariff_schedule': tariff_schedule,
            'horizon_hours': horizon_hours,
            'weight_cost': weight_cost,
            'weight_peak': weight_peak,
            'solver': solver_choice,
            'baseline_schedule': baseline_schedule,
            'optimized_schedule': optimized_schedule,
            'baseline_demand': base_demand_formatted,
            'optimized_demand': opt_demand_formatted,
            'baseline_cost': baseline_cost,
            'optimized_cost': optimized_cost,
            'cost_savings': cost_savings,
            'cost_savings_pct': cost_savings_pct,
            'baseline_peak': baseline_peak,
            'optimized_peak': optimized_peak,
            'peak_reduction': peak_reduction,
            'peak_reduction_pct': peak_reduction_pct,
            'constraint_violations': violations,
            'generated_at': gen_time,
        }

    def run_scenario_comparison(
        self,
        dataset_id: str,
        forecast_id: Optional[str] = None,
        flexible_loads: Optional[List[Dict[str, Any]]] = None,
        tariff_schedule: Optional[List[Dict[str, Any]]] = None,
        horizon_hours: int = 24
    ) -> Dict[str, Any]:
        scenarios = [
            {
                'name': 'Cost Minimization',
                'description': 'Maximizes financial savings by concentrating flexible loads into cheapest off-peak tariff periods.',
                'weight_cost': 1.0,
                'weight_peak': 0.0,
                'solver': 'milp'
            },
            {
                'name': 'Peak Shaving',
                'description': 'Prioritizes grid stability and capacity charge reductions by minimizing maximum hourly peak demand.',
                'weight_cost': 0.0,
                'weight_peak': 1.0,
                'solver': 'heuristic'
            },
            {
                'name': 'Balanced Smart Grid',
                'description': 'Equal trade-off between energy bill savings and peak demand mitigation.',
                'weight_cost': 0.5,
                'weight_peak': 0.5,
                'solver': 'milp'
            },
            {
                'name': 'Demand Response Express',
                'description': 'Rapid priority dispatch designed for fast grid response windows.',
                'weight_cost': 0.7,
                'weight_peak': 0.3,
                'solver': 'priority'
            }
        ]

        results = []
        for sc in scenarios:
            res = self.run_optimization(
                dataset_id=dataset_id,
                forecast_id=forecast_id,
                flexible_loads=flexible_loads,
                tariff_schedule=tariff_schedule,
                horizon_hours=horizon_hours,
                weight_cost=sc['weight_cost'],
                weight_peak=sc['weight_peak'],
                solver=sc['solver']
            )
            results.append({
                'name': sc['name'],
                'description': sc['description'],
                'weight_cost': sc['weight_cost'],
                'weight_peak': sc['weight_peak'],
                'solver': sc['solver'],
                'cost': res['optimized_cost'],
                'cost_savings': res['cost_savings'],
                'cost_savings_pct': res['cost_savings_pct'],
                'peak_demand': res['optimized_peak'],
                'peak_reduction': res['peak_reduction'],
                'peak_reduction_pct': res['peak_reduction_pct'],
                'violations': len(res['constraint_violations']),
                'optimization_id': res['optimization_id']
            })

        return {
            'scenarios': results,
            'horizon_hours': horizon_hours,
            'baseline_cost': results[0]['cost'] + results[0]['cost_savings'] if results else 0.0,
            'baseline_peak': results[0]['peak_demand'] + results[0]['peak_reduction'] if results else 0.0,
        }

    def get_optimization(self, optimization_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM optimizations WHERE id = ?", (optimization_id,))
            row = cursor.fetchone()
            if not row:
                return None

        loads = json.loads(row['flexible_loads']) if row['flexible_loads'] else []
        tariff = json.loads(row['tariff_schedule']) if row['tariff_schedule'] else []
        base_sched = json.loads(row['baseline_schedule']) if row['baseline_schedule'] else []
        opt_sched = json.loads(row['optimized_schedule']) if row['optimized_schedule'] else []
        base_dem = json.loads(row['baseline_demand']) if row['baseline_demand'] else []
        opt_dem = json.loads(row['optimized_demand']) if row['optimized_demand'] else []
        violations = json.loads(row['constraint_violations']) if row['constraint_violations'] else []

        return {
            'id': row['id'],
            'optimization_id': row['id'],
            'dataset_id': row['dataset_id'],
            'forecast_id': row['forecast_id'],
            'flexible_loads': loads,
            'tariff_schedule': tariff,
            'horizon_hours': row['horizon_hours'],
            'weight_cost': row['weight_cost'],
            'weight_peak': row['weight_peak'],
            'solver': row['solver'] if 'solver' in row.keys() else 'milp',
            'baseline_schedule': base_sched,
            'optimized_schedule': opt_sched,
            'baseline_demand': base_dem,
            'optimized_demand': opt_dem,
            'baseline_cost': row['baseline_cost'],
            'optimized_cost': row['optimized_cost'],
            'cost_savings': row['cost_savings'],
            'cost_savings_pct': row['cost_savings_pct'],
            'baseline_peak': row['baseline_peak'],
            'optimized_peak': row['optimized_peak'],
            'peak_reduction': row['peak_reduction'],
            'peak_reduction_pct': row['peak_reduction_pct'],
            'constraint_violations': violations,
            'generated_at': row['created_at'],
        }

    def list_optimizations(self) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM optimizations ORDER BY created_at DESC")
            rows = cursor.fetchall()

        optimizations = []
        for row in rows:
            optimizations.append({
                'id': row['id'],
                'optimization_id': row['id'],
                'dataset_id': row['dataset_id'],
                'forecast_id': row['forecast_id'],
                'horizon_hours': row['horizon_hours'],
                'weight_cost': row['weight_cost'],
                'weight_peak': row['weight_peak'],
                'solver': row['solver'] if 'solver' in row.keys() else 'milp',
                'baseline_cost': row['baseline_cost'],
                'optimized_cost': row['optimized_cost'],
                'cost_savings': row['cost_savings'],
                'cost_savings_pct': row['cost_savings_pct'],
                'baseline_peak': row['baseline_peak'],
                'optimized_peak': row['optimized_peak'],
                'peak_reduction': row['peak_reduction'],
                'peak_reduction_pct': row['peak_reduction_pct'],
                'generated_at': row['created_at'],
            })
        return optimizations