"""Normal, chi-square and t distributions without SciPy (R's pnorm, pchisq, pt and qt give the same values)."""

from __future__ import annotations

import math

ITERATIONS = 300
EPSILON = 1e-15
TINY = 1e-300


def normal_cdf(value: float) -> float:
    return 0.5 * math.erfc(-value / math.sqrt(2))


def gamma_upper(shape: float, value: float) -> float:
    """Regularised upper incomplete gamma Q(shape, value): series below shape + 1, continued fraction above."""
    if value <= 0:
        return 1.0
    log_front = shape * math.log(value) - value - math.lgamma(shape)
    if value < shape + 1:
        term = total = 1.0 / shape
        for step in range(1, ITERATIONS):
            term *= value / (shape + step)
            total += term
            if abs(term) < abs(total) * EPSILON:
                break
        return 1.0 - total * math.exp(log_front)
    b, c, d = value + 1 - shape, 1 / TINY, 1 / (value + 1 - shape)
    result = d
    for step in range(1, ITERATIONS):
        a, b = -step * (step - shape), b + 2
        d, c = 1 / (a * d + b if abs(a * d + b) > TINY else TINY), b + a / c if abs(b + a / c) > TINY else TINY
        result *= d * c
        if abs(d * c - 1) < EPSILON:
            break
    return result * math.exp(log_front)


def chi2_sf(value: float, df: float) -> float:
    return gamma_upper(df / 2, value / 2)


def beta_fraction(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    c, d = 1.0, 1 - (a + b) * x / (a + 1)
    d = 1 / (d if abs(d) > TINY else TINY)
    result = d
    for step in range(1, ITERATIONS):
        for numerator in (step * (b - step) * x / ((a + 2 * step - 1) * (a + 2 * step)),
                          -(a + step) * (a + b + step) * x / ((a + 2 * step) * (a + 2 * step + 1))):
            d = 1 + numerator * d
            d = 1 / (d if abs(d) > TINY else TINY)
            c = 1 + numerator / c
            c = c if abs(c) > TINY else TINY
            result *= d * c
        if abs(d * c - 1) < EPSILON:
            break
    return result


def beta_regularised(a: float, b: float, x: float) -> float:
    if x <= 0 or x >= 1:
        return 0.0 if x <= 0 else 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * beta_fraction(a, b, x) / a
    return 1 - front * beta_fraction(b, a, 1 - x) / b


def t_cdf(value: float, df: float) -> float:
    tail = 0.5 * beta_regularised(df / 2, 0.5, df / (df + value * value))
    return 1 - tail if value > 0 else tail


def t_quantile(probability: float, df: float) -> float:
    """Inverse of t_cdf by bisection; accurate to well below 1e-10."""
    low, high = -1e4, 1e4
    for _ in range(ITERATIONS):
        middle = (low + high) / 2
        if t_cdf(middle, df) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2
