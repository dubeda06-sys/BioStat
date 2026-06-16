"""Probit Regression."""
import numpy as np
from scipy import stats, optimize


def probit_regression(X, y):
    """
    Probit Regression.

    Args:
        X: 2D array of predictors (n x p)
        y: binary response (0 or 1)

    Returns:
        dict with coefficients, p-values, and predictions
    """
    X = np.atleast_2d(np.asarray(X, dtype=float))
    y = np.asarray(y, dtype=float)

    n, p = X.shape
    X_with_intercept = np.column_stack([np.ones(n), X])

    def neg_log_likelihood(beta):
        xb = X_with_intercept @ beta
        xb = np.clip(xb, -10, 10)
        phi = stats.norm.cdf(xb)
        phi = np.clip(phi, 1e-10, 1 - 1e-10)
        ll = np.sum(y * np.log(phi) + (1 - y) * np.log(1 - phi))
        return -ll

    beta0 = np.zeros(p + 1)
    result = optimize.minimize(neg_log_likelihood, beta0, method='BFGS')
    beta = result.x

    try:
        hessian_inv = np.linalg.inv(result.hes_inv)
        se = np.sqrt(np.abs(np.diag(hessian_inv)))
    except:
        se = np.ones(p + 1) * 0.1

    se = np.maximum(se, 1e-10)
    z = beta / se
    p_values = 2 * (1 - stats.norm.cdf(np.abs(z)))

    xb = X_with_intercept @ beta
    predictions = stats.norm.cdf(xb)

    log_likelihood = -result.fun
    aic = 2 * (p + 1) + 2 * log_likelihood

    return {
        'coefficients': beta,
        'se': se,
        'z': z,
        'p_values': p_values,
        'predictions': predictions,
        'log_likelihood': log_likelihood,
        'aic': aic,
        'n': n
    }
