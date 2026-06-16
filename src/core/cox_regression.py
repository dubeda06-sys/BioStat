"""Cox Proportional Hazards Regression."""
import numpy as np
from scipy import optimize


def cox_regression(times, events, covariates):
    """
    Cox Proportional Hazards Regression (Breslow approximation).

    Args:
        times: event/censoring times
        events: event indicators (1=event, 0=censored)
        covariates: 2D array of covariates (n x p)

    Returns:
        dict with hazard ratios, p-values, and log-likelihood
    """
    times = np.asarray(times, dtype=float)
    events = np.asarray(events, dtype=int)
    covariates = np.atleast_2d(np.asarray(covariates, dtype=float))

    n = len(times)
    p = covariates.shape[1]

    order = np.argsort(times)[::-1]
    times = times[order]
    events = events[order]
    covariates = covariates[order]

    def neg_log_likelihood(beta):
        xb = covariates @ beta
        exp_xb = np.exp(xb)
        risk_set_sum = np.cumsum(exp_xb)[::-1]
        risk_set_sum = np.maximum(risk_set_sum, 1e-10)
        ll = np.sum(events * (xb - np.log(risk_set_sum)))
        return -ll

    beta0 = np.zeros(p)
    result = optimize.minimize(neg_log_likelihood, beta0, method='BFGS')
    beta = result.x

    hessian_inv = np.linalg.inv(result.hes_inv) if hasattr(result, 'hes_inv') else np.eye(p) * 0.01
    se = np.sqrt(np.abs(np.diag(hessian_inv)))
    se = np.maximum(se, 1e-10)

    z = beta / se
    p_values = 2 * (1 - stats.norm.cdf(np.abs(z)))

    hr = np.exp(beta)
    hr_ci_low = np.exp(beta - 1.96 * se)
    hr_ci_high = np.exp(beta + 1.96 * se)

    log_likelihood = -result.fun
    aic = 2 * p + 2 * log_likelihood

    return {
        'coefficients': beta,
        'hazard_ratios': hr,
        'se': se,
        'z': z,
        'p_values': p_values,
        'hr_ci_low': hr_ci_low,
        'hr_ci_high': hr_ci_high,
        'log_likelihood': log_likelihood,
        'aic': aic,
        'n': n,
        'events': np.sum(events)
    }
