# coding: utf-8
"""Provides a `duplicates_allclose` for finding duplicates in a
DataFrame with tolerances.

"""

from toolz.curried import curry, compose
import pandas as pd
import numpy as np

__all__ = ['duplicates_allclose']

pdapply = curry(pd.DataFrame.apply)  # pylint: disable=invalid-name
sort_values = curry(pd.DataFrame.sort_values)  # pylint: disable=invalid-name
pdall = curry(pd.DataFrame.all)  # pylint: disable=invalid-name
duplicated = curry(pd.DataFrame.duplicated)  # pylint: disable=invalid-name
diff = curry(pd.DataFrame.diff)  # pylint: disable=invalid-name
npappend = curry(np.append)  # pylint: disable=invalid-name


def sequence(*args):
    """Compose functions in order

    Args:
      args: the functions to compose

    Returns:
      composed functions

    >>> assert sequence(lambda x: x + 1, lambda x: x * 2)(3) == 8
    """
    return compose(*args[::-1])


@curry
def debug(statement, value):
    """Useful debug for functional programming
    """
    print()
    print(statement)
    print(value)
    return value


def find_duplicates_col(dataframe):
    """Find duplicates column by column.

    Args:
      dataframe: a dataframe

    Returns:
      a dataframe of the same shape but with bool values indicating
      neighboring duplicates in the same column

    >>> find_duplicates_col(pd.DataFrame(
    ...     dict(A=['a', 'a', 'd'],
    ...          B=['b', 'd', 'b'],
    ...          C=['d', 'c', 'c'],
    ...          D=[  1,   1,   1],
    ...          E=[  1,   2,   1])
    ... ))
           A      B      C      D      E
    0  False  False  False  False  False
    1   True  False  False   True  False
    2  False  False   True   True  False

    """
    return dataframe.apply(
        sequence(np.array, lambda x: x[:-1] == x[1:], npappend([False])), axis=0
    )


@curry
def duplicate_if_close(dataframe, fcols):
    """Find neighboring column duplicates based tolerances.

    This only works with data frames containing numbers.

    Args:
      dataframe: a dataframe
      fcols: the absolute tolerances

    Returns:
      a dataframe of the same shape but with bool values indicating
      neighboring close values in the same column

    >>> duplicate_if_close(pd.DataFrame(
    ...     dict(A=[1.01, 1.02, 1.03],
    ...          B=[1.1, 1.0, 0.99],
    ...          C=[1, 1.1, 1.2],
    ...          D=[  1,   1,   1],
    ...          E=[  1,   2,   1])
    ... ), dict(A=0.02, B=0.02, C=0.02, D=0.02, E=0.02))
           A      B      C      D      E
    0  False  False  False  False  False
    1   True  False  False   True  False
    2   True   True  False   True  False

    """
    return sequence(
        diff, pdapply(func=lambda x: np.absolute(x) <= fcols[x.name], axis=0)
    )(dataframe)


@curry
def fduplicates(dcols, fcols, dataframe):
    """Check for mixture of exact duplicates and closeness

    Args:
      dcols: the columns to check for exact duplicates
      fcols: the columns to check for closeness, a dict with column names as
       keys and tolerances as values
      dataframe: the dataframe

    Returns:
      a dataframe of the same shape but with bool values indicating
      neighboring close values in the same column

    >>> fduplicates(
    ...     dcols=['C', 'D', 'E'],
    ...     fcols=dict(A=0.02, B=0.02),
    ...     dataframe=pd.DataFrame(
    ...         dict(A=[1.01, 1.02, 1.03],
    ...              B=[1.1, 1.0, 0.99],
    ...              C=[1, 1.1, 'b'],
    ...              D=[  'a',   'a',   'a'],
    ...              E=[  1,   2,   1])
    ...     )
    ... )
           A      B      C      D      E
    0  False  False  False  False  False
    1   True  False  False   True  False
    2   True   True  False   True  False

    """
    return pd.concat(
        [
            duplicate_if_close(dataframe[list(fcols.keys())], fcols),
            find_duplicates_col(dataframe[dcols]),
        ],
        axis=1,
    )


@curry
def duplicates_allclose(dataframe, dcols, fcols):
    """
    Determine duplicates in dataframe based on tolerances.  The implementation
    first uses `pandas.DataFrame.duplicated` on the `dcols` argument with
    `keep=False` to keep all duplicates.  The duplicate sub-dataframe is then
    sorted on both `dcols` and `fcols`.  A diff between each row is then done
    on the sorted duplicates dataframe.  The float values are then checked for
    their tolerances.
    
    Note: False duplicates may be identified if tolerance ranges overlap.
    Consider dataframe with rows 1,2,3.  If row 2 matches row 1 within the
    tolerances, and row 3 matches row 2 within the tolerances, both rows 2 and
    3 will be labeled as tolerances even if row 3 does not match row 1 within
    the tolerances.
    
    Parameters
    ----------
    dataframe : pandas.DataFrame
        The dataframe to search for duplicates
    dcols : list
        The column names that are tested for exact duplicates.
    fcols : dict
        The column names (keys) that are tested using absolute tolerances
        (values).
    
    Returns
    -------
    list of bool of length nrows
        False for first occurrence of checked values, True for subsequent
        duplicates.
    """

    alltrue = lambda x: [True] * len(x)

    func = sequence(
        duplicated(subset=dcols, keep=False) if dcols else alltrue,
        lambda x: dataframe[x],
        sort_values(by=dcols + list(fcols.keys())),
        fduplicates(dcols, fcols), # pylint: disable=no-value-for-parameter
        pdapply(func=pdall, axis=1),
    )

    return (
        dataframe.assign(duplicates=func(dataframe)).duplicates.fillna(False).rename()
    )
