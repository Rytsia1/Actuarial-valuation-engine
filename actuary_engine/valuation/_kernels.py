"""
JIT-compiled numerical valuation kernels for GPV roll-back discounting and portfolio batch matrix operations.

Uses Numba's @njit(fastmath=True, nogil=True) for C-speed compilation with graceful
pure-Python fallback if Numba is unavailable.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

try:
    from numba import njit  # type: ignore[import-untyped]
    HAS_NUMBA = True
except ImportError:  # pragma: no cover
    def njit(*args: Any, **kwargs: Any) -> Callable[..., Any]:
        """Fallback no-op decorator when Numba is not installed."""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator
    HAS_NUMBA = False


@njit(fastmath=True, nogil=True)
def _rollback_gpv_kernel(
    death_claims: np.ndarray,
    lapse_payouts: np.ndarray,
    maturity_benefits: np.ndarray,
    expenses: np.ndarray,
    premiums: np.ndarray,
    qx_dep: np.ndarray,
    wx_dep: np.ndarray,
    discount_v: float,
    max_t: int,
) -> np.ndarray:
    """Backward induction rollout kernel for GPV reserve trajectory.

    V_t = (Outgo_t - Premium_t) + V_{t+1} * (1 - q_t - w_t) * v
    with terminal boundary V_n = 0.0.
    """
    reserves = np.zeros(max_t + 1, dtype=np.float64)
    reserves[max_t] = 0.0

    for t in range(max_t - 1, -1, -1):
        outgo_t = death_claims[t] + lapse_payouts[t] + maturity_benefits[t] + expenses[t]
        inflow_t = premiums[t]
        ncf_t = outgo_t - inflow_t

        p_ap = max(0.0, 1.0 - qx_dep[t] - wx_dep[t])
        reserves[t] = ncf_t + reserves[t + 1] * p_ap * discount_v

    return reserves


@njit(fastmath=True, nogil=True)
def _portfolio_batch_rollout_kernel(
    issue_ages: np.ndarray,
    term_years: np.ndarray,
    sums_assured: np.ndarray,
    gross_premiums: np.ndarray,
    product_type_codes: np.ndarray,  # 0=term, 1=endowment, 2=whole_life, 3=pure_endowment
    qx_matrix: np.ndarray,          # shape (num_policies, max_proj_years)
    base_lapses: np.ndarray,        # shape (max_proj_years,)
    discount_factors_boy: np.ndarray,
    discount_factors_eoy: np.ndarray,
    expense_first_pct: float,
    expense_renewal_pct: float,
    expense_first_flat: float,
    expense_renewal_flat: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """High-throughput vectorized batch kernel across thousands of policy contracts.

    Returns:
        Tuple of (pvfb_arr, pvfp_arr, pvfe_arr, bel_arr).
    """
    n_policies = len(issue_ages)
    max_proj = len(discount_factors_boy)

    pvfb_arr = np.zeros(n_policies, dtype=np.float64)
    pvfp_arr = np.zeros(n_policies, dtype=np.float64)
    pvfe_arr = np.zeros(n_policies, dtype=np.float64)
    bel_arr = np.zeros(n_policies, dtype=np.float64)

    for i in range(n_policies):
        face = sums_assured[i]
        gp = gross_premiums[i]
        n = term_years[i]
        p_code = product_type_codes[i]

        inforce = 1.0
        p_pvfb = 0.0
        p_pvfp = 0.0
        p_pvfe = 0.0

        proj_len = min(max_proj, n)

        for t in range(proj_len):
            w_t = base_lapses[t]
            q_t = qx_matrix[i, t]

            q_dep = q_t * (1.0 - 0.5 * w_t)
            w_dep = w_t * (1.0 - 0.5 * q_t)

            deaths = inforce * q_dep
            is_mat_year = (t == n - 1) and (p_code == 1 or p_code == 3)
            survivors = inforce * max(0.0, 1.0 - q_dep - w_dep) if is_mat_year else 0.0

            # Death claims & maturity
            claims = deaths * face if (p_code == 0 or p_code == 1 or p_code == 2) else 0.0
            mat_pay = survivors * face if is_mat_year else 0.0

            # Premiums
            prem = inforce * gp

            # Expenses
            pct_exp = expense_first_pct if t == 0 else expense_renewal_pct
            flat_exp = expense_first_flat if t == 0 else expense_renewal_flat
            exp_t = inforce * (gp * pct_exp + flat_exp)

            disc_eoy = discount_factors_eoy[t]
            disc_boy = discount_factors_boy[t]

            p_pvfb += (claims + mat_pay) * disc_eoy
            p_pvfp += prem * disc_boy
            p_pvfe += exp_t * disc_boy

            inforce = inforce * max(0.0, 1.0 - q_dep - w_dep)

        pvfb_arr[i] = p_pvfb
        pvfp_arr[i] = p_pvfp
        pvfe_arr[i] = p_pvfe
        bel_arr[i] = p_pvfb + p_pvfe - p_pvfp

    return pvfb_arr, pvfp_arr, pvfe_arr, bel_arr
