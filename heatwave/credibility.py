"""Joint Gaussian conditioning for spatially dependent engineering states.

This is a mathematical building block, not evidence that headroom is Gaussian
or that engineering uncertainty is sufficient to set insurance credibility.
"""
import numpy as np


def gaussian_posterior(mean, covariance, observation, error_covariance):
    """Return E[H|y] and Cov[H|y] for y=H+e and independent Gaussian e.

    Both covariance matrices can be spatially correlated. No componentwise
    floor/truncation is imposed; that requires a different observation model.
    Sample a fixed asset state in an outer portfolio draw, not afresh each year.
    """
    mean, y = np.asarray(mean, float), np.asarray(observation, float)
    sigma, noise = np.asarray(covariance, float), np.asarray(error_covariance, float)
    n = mean.size
    if mean.shape != (n,) or y.shape != (n,) or sigma.shape != (n, n) or noise.shape != (n, n):
        raise ValueError("Incompatible state, observation or covariance dimensions")
    if not all(np.isfinite(x).all() for x in (mean, y, sigma, noise)):
        raise ValueError("Inputs must be finite")
    for label, matrix in (("prior", sigma), ("measurement", noise)):
        if not np.allclose(matrix, matrix.T, atol=1e-10):
            raise ValueError(f"{label} covariance must be symmetric")
        if np.linalg.eigvalsh(matrix).min() < -1e-10:
            raise ValueError(f"{label} covariance must be positive semidefinite")
    gain = np.linalg.solve(sigma + noise, sigma).T
    posterior_mean = mean + gain @ (y - mean)
    posterior_covariance = sigma - gain @ sigma
    posterior_covariance = (posterior_covariance + posterior_covariance.T) / 2
    return posterior_mean, posterior_covariance
