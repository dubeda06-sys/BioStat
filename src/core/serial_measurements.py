"""Serial Measurements Analysis."""
import numpy as np
from scipy import stats


def serial_measurements_summary(data):
    """
    Summarize serial measurements across subjects.

    Args:
        data: 2D array (subjects x time_points)

    Returns:
        dict with means, slopes, and individual trajectories
    """
    data = np.asarray(data, dtype=float)
    n, k = data.shape

    means = np.mean(data, axis=0)
    sds = np.std(data, axis=0, ddof=1)
    sems = sds / np.sqrt(n)

    time_points = np.arange(k)
    slopes = np.zeros(n)
    for i in range(n):
        valid = ~np.isnan(data[i])
        if np.sum(valid) >= 2:
            slope, _, _, _, _ = stats.linregress(time_points[valid], data[i, valid])
            slopes[i] = slope

    overall_slope, _, r_value, p_value, _ = stats.linregress(
        np.tile(time_points, n), data.flatten()
    )

    individual_trajectories = []
    for i in range(n):
        valid = ~np.isnan(data[i])
        if np.sum(valid) >= 2:
            slope, intercept, _, _, _ = stats.linregress(time_points[valid], data[i, valid])
            individual_trajectories.append({
                'subject': i + 1,
                'slope': slope,
                'intercept': intercept,
                'values': data[i].tolist()
            })

    return {
        'means': means.tolist(),
        'sds': sds.tolist(),
        'sems': sems.tolist(),
        'slopes': slopes.tolist(),
        'mean_slope': np.mean(slopes),
        'sd_slope': np.std(slopes, ddof=1),
        'overall_slope': overall_slope,
        'overall_r': r_value,
        'overall_p': p_value,
        'individual_trajectories': individual_trajectories,
        'n_subjects': n,
        'n_timepoints': k
    }
