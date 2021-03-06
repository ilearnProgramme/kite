import numpy as num

from .meta import SandboxSourceRectangular, SandboxSource, SourceProcessor
from pyrocko.guts import String, Float, Int
from pyrocko import gf

d2r = num.pi / 180.
r2d = 180. / num.pi
km = 1e3


class PyrockoSource(object):

    def parametersUpdated(self):
        self.updatePyrockoSource()
        SandboxSource.parametersUpdated(self)

    def updatePyrockoSource(self):
        for arg, value in self._src_args.iteritems():
            self.pyrocko_source.__setattr__(arg, value)


class PyrockoRectangularSource(SandboxSourceRectangular, PyrockoSource):

    __implements__ = 'pyrocko'

    decimation_factor = Int.T(
        optional=True,
        default=10,
        help='Sub-source decimation factor.')
    store_dir = String.T(
        help='Pyrocko GF Store path')

    parametersUpdated = PyrockoSource.parametersUpdated

    def __init__(self, *args, **kwargs):
        SandboxSourceRectangular.__init__(self, *args, **kwargs)
        self.pyrocko_source = gf.RectangularSource(**self._src_args)

    @property
    def _src_args(self):
        return {
            'lat': 0.,
            'lon': 0.,
            'north_shift': self.northing,
            'east_shift': self.easting,
            'depth': self.depth,
            'length': self.length,
            'width': self.width,
            'strike': self.strike,
            'dip': self.dip,
            'rake': self.rake,
            'slip': self.slip,
            'decimation_factor': self.decimation_factor,
            'anchor': 'top',
        }


class PyrockoMomentTensor(SandboxSource, PyrockoSource):

    __implements__ = 'pyrocko'

    store_dir = String.T(
        help='Pyrocko GF Store path')
    mnn = Float.T(
        default=1.,
        help='north-north component of moment tensor in [Nm]')
    mee = Float.T(
        default=1.,
        help='east-east component of moment tensor in [Nm]')
    mdd = Float.T(
        default=1.,
        help='down-down component of moment tensor in [Nm]')
    mne = Float.T(
        default=0.,
        help='north-east component of moment tensor in [Nm]')
    mnd = Float.T(
        default=0.,
        help='north-down component of moment tensor in [Nm]')
    med = Float.T(
        default=0.,
        help='east-down component of moment tensor in [Nm]')

    parametersUpdated = PyrockoSource.parametersUpdated

    def __init__(self, *args, **kwargs):
        SandboxSource.__init__(self, *args, **kwargs)
        self.pyrocko_source = gf.MTSource(**self._src_args)

    @property
    def _src_args(self):
        return {
            'lat': 0.,
            'lon': 0.,
            'north_shift': self.northing,
            'east_shift': self.easting,
            'depth': self.depth,
            'mnn': self.mnn,
            'mee': self.mee,
            'mdd': self.mdd,
            'mne': self.mne,
            'mnd': self.mnd,
            'med': self.med,
        }


class PyrockoDoubleCouple(SandboxSource, PyrockoSource):

    __implements__ = 'pyrocko'

    strike = Float.T(
        default=0.0,
        help='strike direction in [deg], measured clockwise from north')
    magnitude = Float.T(
        default=6.0,
        help='moment magnitude Mw as in [Hanks and Kanamori, 1979]')
    dip = Float.T(
        default=90.0,
        help='dip angle in [deg], measured downward from horizontal')
    rake = Float.T(
        default=0.0,
        help='rake angle in [deg], '
             'measured counter-clockwise from right-horizontal '
             'in on-plane view')
    store_dir = String.T(
        help='Pyrocko GF Store path')

    parametersUpdated = PyrockoSource.parametersUpdated

    def __init__(self, *args, **kwargs):
        SandboxSource.__init__(self, *args, **kwargs)
        self.pyrocko_source = gf.DCSource(**self._src_args)

    @property
    def moment(self):
        return self.pyrocko_source.moment

    @property
    def _src_args(self):
        return {
            'lat': 0.,
            'lon': 0.,
            'north_shift': self.northing,
            'east_shift': self.easting,
            'depth': self.depth,
            'magnitude': self.magnitude,
            'strike': self.strike,
            'dip': self.dip,
            'rake': self.rake
        }


class PyrockoRingfaultSource(SandboxSource, PyrockoSource):

    __implements__ = 'pyrocko'

    store_dir = String.T(
        help='Pyrocko GF Store path')
    diameter = Float.T(
        default=1.0,
        help='diameter of the ring in [m]')
    sign = Float.T(
        default=1.0,
        help='inside of the ring moves up (+1) or down (-1)')
    strike = Float.T(
        default=0.0,
        help='strike direction of the ring plane, clockwise from north,'
             ' in [deg]')
    dip = Float.T(
        default=0.0,
        help='dip angle of the ring plane from horizontal in [deg]')
    npointsources = Int.T(
        default=8,
        help='number of point sources to use')
    magnitude = Float.T(
        default=6.0,
        help='moment magnitude Mw as in [Hanks and Kanamori, 1979]')

    parametersUpdated = PyrockoSource.parametersUpdated

    def __init__(self, *args, **kwargs):
        SandboxSource.__init__(self, *args, **kwargs)
        self.pyrocko_source = gf.RingfaultSource(**self._src_args)

    @property
    def _src_args(self):
        return {
            'lat': 0.,
            'lon': 0.,
            'north_shift': self.northing,
            'east_shift': self.easting,
            'depth': self.depth,
            'diameter': self.diameter,
            'strike': self.strike,
            'dip': self.dip,
            'magnitude': self.magnitude,
            'npointsources': self.npointsources,
        }


class PyrockoProcessor(SourceProcessor):

    __implements__ = 'pyrocko'

    def __init__(self, *args):
        SourceProcessor.__init__(self, *args)
        self.engine = gf.LocalEngine()

    def process(self, sources, coords, nthreads=0):
        result = {
            'processor_profile': dict(),
            'displacement.n': num.zeros((coords.shape[0])),
            'displacement.e': num.zeros((coords.shape[0])),
            'displacement.d': num.zeros((coords.shape[0]))
        }

        target = gf.StaticTarget(
            east_shifts=coords[:, 0],
            north_shifts=coords[:, 1],
            interpolation='nearest_neighbor')

        for store_dir in set([src.store_dir for src in sources]):
            self.engine.store_dirs = [store_dir]

            pyr_sources = [src.pyrocko_source for src in sources
                           if src.store_dir == store_dir]

            for src in pyr_sources:
                src.regularize()

            try:
                res = self.engine.process(
                    pyr_sources, [target],
                    nthreads=nthreads)
            except Exception as e:
                self._log.error(
                    'Could not execute pyrocko.gf.LocalEngine.process! \n'
                    'LocalEngine Exception: %s' % e)
                continue

            for static_res in res.static_results():
                result['displacement.n'] += static_res.result['displacement.n']
                result['displacement.e'] += static_res.result['displacement.e']
                result['displacement.d'] += static_res.result['displacement.d']

        return result
