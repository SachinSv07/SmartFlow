def calculate_signal_time(weighted_score, thresholds):
    """
    Decide green signal duration based on weighted density score.
    Args:
        weighted_score (int): Weighted vehicle density score.
        thresholds (list): List of (min, max, duration) tuples.
    Returns:
        int: Recommended green signal duration in seconds.
    """
    for min_val, max_val, duration in thresholds:
        if min_val <= weighted_score <= max_val:
            return duration
    return thresholds[-1][2]  # Default to max duration
