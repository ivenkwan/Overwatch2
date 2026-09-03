"""Concrete :class:`GraphProfile` instances for the two physical graphs.

Importing this subpackage constructs both profiles, which runs the
:class:`GraphProfile` validation (rail-source exclusivity, epoch ts). A
construct-time error here means a profile is mis-specified — fail at import.
"""

from .aml_network import AML_NETWORK
from .tap_and_go import TAP_AND_GO

__all__ = ["AML_NETWORK", "TAP_AND_GO"]
