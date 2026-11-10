"""Empirical risk metrics with exact probability mass handling at quantile ties."""
import numpy as np


def empirical_tail(losses, q=0.995):
    """VaR and ES of the equally weighted empirical distribution.

    VaR is the left quantile (inverse empirical CDF). ES integrates the upper
    1-q probability mass, including only the necessary fraction at the boundary.
    Capital is a single-peril proxy, not the regulatory Solvency II SCR.
    """
    x = np.asarray(losses, dtype=float)
    if x.ndim != 1 or not x.size or not np.isfinite(x).all() or np.any(x < 0):
        raise ValueError("Expected a non-empty vector of finite nonnegative losses")
    if not 0 < q < 1:
        raise ValueError("q must lie strictly between zero and one")
    s = np.sort(x)
    var = s[int(np.ceil(q * len(s))) - 1]
    upper_mass = (1 - q) * len(s)
    whole = int(np.floor(upper_mass))
    fraction = upper_mass - whole
    es_sum = s[-whole:].sum() if whole else 0.0
    if fraction > 1e-12:
        es_sum += fraction * s[-whole - 1]
    return dict(aal=float(s.mean()), var=float(var), es=float(es_sum / upper_mass),
                capital_proxy=float(max(var - s.mean(), 0)))


def funding_shortfall(losses, expected_loss_allowance, capital):
    """Evaluate funding against the SAME held-out loss vector for every model."""
    x = np.asarray(losses, float)
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all() or np.any(x < 0):
        raise ValueError("Invalid loss vector")
    if not np.isfinite(expected_loss_allowance) or not np.isfinite(capital) or min(expected_loss_allowance, capital) < 0:
        raise ValueError("Funding must be finite and nonnegative")
    excess = np.maximum(x - expected_loss_allowance - capital, 0)
    return dict(shortfall_probability=float(np.mean(excess > 0)),
                expected_unfunded_loss=float(excess.mean()))
