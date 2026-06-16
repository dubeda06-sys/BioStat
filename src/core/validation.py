"""Input validation for BioStat."""
import numpy as np
import pandas as pd


def validate_numeric_data(data, min_values=2, name="data"):
    """
    Validate that data is numeric and has minimum number of values.

    Args:
        data: array-like input
        min_values: minimum number of non-NaN values required
        name: name for error messages

    Returns:
        tuple: (is_valid, cleaned_data, error_message)
    """
    if data is None or len(data) == 0:
        return False, None, f"{name}: No data provided"

    try:
        arr = np.asarray(data, dtype=float)
    except (ValueError, TypeError):
        return False, None, f"{name}: Data must be numeric"

    arr = arr[~np.isnan(arr)]

    if len(arr) < min_values:
        return False, None, f"{name}: Need at least {min_values} values, got {len(arr)}"

    return True, arr, None


def validate_paired_data(d1, d2, min_pairs=2):
    """
    Validate paired data for two-sample tests.

    Args:
        d1: first array
        d2: second array
        min_pairs: minimum number of paired observations

    Returns:
        tuple: (is_valid, cleaned_d1, cleaned_d2, error_message)
    """
    if d1 is None or d2 is None:
        return False, None, None, "Both variables must be provided"

    try:
        arr1 = np.asarray(d1, dtype=float)
        arr2 = np.asarray(d2, dtype=float)
    except (ValueError, TypeError):
        return False, None, None, "Data must be numeric"

    # Align and remove NaN pairs
    valid = ~(np.isnan(arr1) | np.isnan(arr2))
    arr1, arr2 = arr1[valid], arr2[valid]

    if len(arr1) < min_pairs:
        return False, None, None, f"Need at least {min_pairs} paired values, got {len(arr1)}"

    return True, arr1, arr2, None


def validate_groups(groups, min_groups=2, min_per_group=1):
    """
    Validate group data for ANOVA-type tests.

    Args:
        groups: list of arrays
        min_groups: minimum number of groups
        min_per_group: minimum values per group

    Returns:
        tuple: (is_valid, cleaned_groups, error_message)
    """
    if groups is None or len(groups) < min_groups:
        return False, None, f"Need at least {min_groups} groups"

    cleaned = []
    for i, g in enumerate(groups):
        try:
            arr = np.asarray(g, dtype=float)
            arr = arr[~np.isnan(arr)]
            if len(arr) < min_per_group:
                return False, None, f"Group {i+1}: Need at least {min_per_group} values"
            cleaned.append(arr)
        except (ValueError, TypeError):
            return False, None, f"Group {i+1}: Data must be numeric"

    return True, cleaned, None


def validate_binary_outcome(y, name="outcome"):
    """
    Validate binary outcome variable (0/1).

    Args:
        y: array-like
        name: name for error messages

    Returns:
        tuple: (is_valid, cleaned_data, error_message)
    """
    if y is None or len(y) == 0:
        return False, None, f"{name}: No data provided"

    try:
        arr = np.asarray(y, dtype=float)
    except (ValueError, TypeError):
        return False, None, f"{name}: Data must be numeric"

    arr = arr[~np.isnan(arr)]

    unique = np.unique(arr)
    if not all(u in [0, 1] for u in unique):
        return False, None, f"{name}: Must contain only 0 and 1. Found: {unique.tolist()}"

    if len(arr) < 2:
        return False, None, f"{name}: Need at least 2 values"

    return True, arr, None


def validate_positive_values(data, name="data"):
    """
    Validate that all values are positive.

    Args:
        data: array-like
        name: name for error messages

    Returns:
        tuple: (is_valid, cleaned_data, error_message)
    """
    if data is None or len(data) == 0:
        return False, None, f"{name}: No data provided"

    try:
        arr = np.asarray(data, dtype=float)
    except (ValueError, TypeError):
        return False, None, f"{name}: Data must be numeric"

    arr = arr[~np.isnan(arr)]

    if len(arr) == 0:
        return False, None, f"{name}: No valid values"

    if np.any(arr <= 0):
        return False, None, f"{name}: All values must be positive"

    return True, arr, None


def validate_range(value, min_val, max_val, name="value"):
    """
    Validate that a value is within a range.

    Args:
        value: numeric value
        min_val: minimum allowed value
        max_val: maximum allowed value
        name: name for error messages

    Returns:
        tuple: (is_valid, error_message)
    """
    if value is None:
        return False, f"{name}: Value is required"

    try:
        val = float(value)
    except (ValueError, TypeError):
        return False, f"{name}: Must be numeric"

    if val < min_val or val > max_val:
        return False, f"{name}: Must be between {min_val} and {max_val}"

    return True, None


def validate_contingency_table(table):
    """
    Validate contingency table for chi-square tests.

    Args:
        table: 2D array-like

    Returns:
        tuple: (is_valid, cleaned_table, error_message)
    """
    if table is None or len(table) == 0:
        return False, None, "No data provided"

    try:
        arr = np.asarray(table, dtype=float)
    except (ValueError, TypeError):
        return False, None, "Data must be numeric"

    if arr.ndim != 2:
        return False, None, "Data must be 2-dimensional"

    if arr.shape[0] < 2 or arr.shape[1] < 2:
        return False, None, "Table must be at least 2x2"

    if np.any(arr < 0):
        return False, None, "Table values must be non-negative"

    return True, arr, None


def get_validation_summary(data, name="data"):
    """
    Get comprehensive validation summary for data.

    Args:
        data: array-like
        name: name for display

    Returns:
        dict with validation results
    """
    if data is None:
        return {'valid': False, 'error': 'No data'}

    try:
        arr = np.asarray(data, dtype=float)
    except:
        return {'valid': False, 'error': 'Not numeric'}

    total = len(arr)
    valid = np.sum(~np.isnan(arr))
    missing = total - valid

    return {
        'valid': True,
        'total': total,
        'valid_count': valid,
        'missing': missing,
        'missing_pct': (missing / total * 100) if total > 0 else 0,
        'min': float(np.nanmin(arr)) if valid > 0 else None,
        'max': float(np.nanmax(arr)) if valid > 0 else None,
        'mean': float(np.nanmean(arr)) if valid > 0 else None,
        'std': float(np.nanstd(arr, ddof=1)) if valid > 1 else None,
    }
