#!/usr/bin/python2
from __future__ import division, absolute_import, print_function, \
    unicode_literals
from .utils_qt import SliderWidgetParameterItem
from .common import QKiteView, QKitePlot, QKiteParameterGroup

import pyqtgraph as pg
import pyqtgraph.parametertree.parameterTypes as pTypes


class QKiteQuadtree(QKiteView):
    def __init__(self, spool):
        scene_proxy = spool.scene_proxy
        self.title = 'Scene.quadtree'
        self.main_widget = QKiteQuadtreePlot(scene_proxy)
        self.tools = {}

        self.param_quadtree = QKiteParamQuadtree(scene_proxy,
                                                 self.main_widget,
                                                 expanded=True)
        self.parameters = [self.param_quadtree]

        scene_proxy.sigSceneModelChanged.connect(self.modelChanged)

        QKiteView.__init__(self)

    def modelChanged(self):
        self.main_widget.update()
        self.main_widget.transFromFrame()
        self.main_widget.updateFocalPoints()

        self.param_quadtree.updateValues()
        self.param_quadtree.onConfigUpdate()
        self.param_quadtree.updateEpsilonLimits()


class QKiteQuadtreePlot(QKitePlot):
    def __init__(self, scene_proxy):

        self.components_available = {
            'mean':
            ['Node.mean displacement',
             lambda sp: sp.quadtree.leaf_matrix_means],
            'median':
            ['Node.median displacement',
             lambda sp: sp.quadtree.leaf_matrix_medians],
            'weight':
            ['Node.weight covariance',
             lambda sp: sp.quadtree.leaf_matrix_weights],
        }

        self._component = 'median'

        QKitePlot.__init__(self, scene_proxy=scene_proxy)

        # http://paletton.com
        focalpoint_color = (45, 136, 45)
        # focalpoint_outline_color = (255, 255, 255, 200)
        focalpoint_outline_color = (3, 212, 3)
        self.focal_points =\
            pg.ScatterPlotItem(size=3.,
                               pen=pg.mkPen(focalpoint_outline_color,
                                            width=.5),
                               brush=pg.mkBrush(focalpoint_color),
                               antialias=True)

        self.addItem(self.focal_points)

        self.scene_proxy.sigQuadtreeChanged.connect(self.update)
        self.scene_proxy.sigQuadtreeChanged.connect(self.updateFocalPoints)
        # self.scene_proxy.sigFrameChanged.connect(self.transFromFrame)
        # self.scene_proxy.sigFrameChanged.connect(self.transFromFrameScatter)

        self.updateFocalPoints()

    def transFromFrameScatter(self):
        self.focal_points.resetTransform()
        self.focal_points.scale(
            self.scene_proxy.frame.dE, self.scene_proxy.frame.dN)

    def updateFocalPoints(self):
        if self.scene_proxy.quadtree.leaf_focal_points.size == 0:
            self.focal_points.clear()
        else:
            self.focal_points.setData(
                pos=self.scene_proxy.quadtree.leaf_focal_points,
                pxMode=True)


class QKiteParamQuadtree(QKiteParameterGroup):
    def __init__(self, scene_proxy, plot, *args, **kwargs):
        self.plot = plot
        self.sig_guard = True
        self.sp = scene_proxy

        kwargs['type'] = 'group'
        kwargs['name'] = 'Scene.quadtree'
        self.parameters = ['nleafs', 'nnodes', 'epsilon_limit']
        scene_proxy.sigQuadtreeConfigChanged.connect(self.onConfigUpdate)
        scene_proxy.sigQuadtreeChanged.connect(self.updateValues)

        QKiteParameterGroup.__init__(self,
                                     model=scene_proxy,
                                     model_attr='quadtree',
                                     **kwargs)

        def updateGuard(func):
            def wrapper(*args, **kwargs):
                if not self.sig_guard:
                    func()
            return wrapper

        # Epsilon control
        @updateGuard
        def updateEpsilon():
            scene_proxy.quadtree.epsilon = self.epsilon.value()

        p = {'name': 'epsilon',
             'value': scene_proxy.quadtree.epsilon,
             'type': 'float',
             'step': round((scene_proxy.quadtree.epsilon -
                            scene_proxy.quadtree.epsilon_limit)*.1, 3),
             'limits': (scene_proxy.quadtree.epsilon_limit,
                        2*scene_proxy.quadtree.epsilon),
             'editable': True}
        self.epsilon = pTypes.SimpleParameter(**p)
        self.epsilon.itemClass = SliderWidgetParameterItem
        self.epsilon.sigValueChanged.connect(updateEpsilon)

        # Epsilon control
        @updateGuard
        def updateNanFrac():
            scene_proxy.quadtree.nan_allowed = self.nan_allowed.value()

        p = {'name': 'nan_allowed',
             'value': scene_proxy.quadtree.nan_allowed,
             'type': 'float',
             'step': 0.05,
             'limits': (0., 1.),
             'editable': True, }
        self.nan_allowed = pTypes.SimpleParameter(**p)
        self.nan_allowed.itemClass = SliderWidgetParameterItem
        self.nan_allowed.sigValueChanged.connect(updateNanFrac)

        # Tile size controls
        @updateGuard
        def updateTileSizeMin():
            scene_proxy.quadtree.tile_size_min = self.tile_size_min.value()

        p = {'name': 'tile_size_min',
             'value': scene_proxy.quadtree.tile_size_min,
             'type': 'int',
             'limits': (50, 50000),
             'step': 100,
             'editable': True,
             'siPrefix': 'm'}
        self.tile_size_min = pTypes.SimpleParameter(**p)
        self.tile_size_min.itemClass = SliderWidgetParameterItem

        @updateGuard
        def updateTileSizeMax():
            scene_proxy.quadtree.tile_size_max = self.tile_size_max.value()

        p.update({'name': 'tile_size_max',
                  'value': scene_proxy.quadtree.tile_size_max})
        self.tile_size_max = pTypes.SimpleParameter(**p)
        self.tile_size_max.itemClass = SliderWidgetParameterItem

        self.tile_size_min.sigValueChanged.connect(updateTileSizeMin)
        self.tile_size_max.sigValueChanged.connect(updateTileSizeMax)

        # Component control
        def changeComponent():
            self.plot.component = self.components.value()

        p = {'name': 'display',
             'values': {
                'QuadNode.mean': 'mean',
                'QuadNode.median': 'median',
                'QuadNode.weight': 'weight',
             },
             'value': 'mean'}
        self.components = pTypes.ListParameter(**p)
        self.components.sigValueChanged.connect(changeComponent)

        def changeSplitMethod():
            scene_proxy.quadtree.setSplitMethod(scene_proxylit_method.value())

        p = {'name': 'setSplitMethod',
             'values': {
                'Mean Std (Sigurjonson, 2001)': 'mean_std',
                'Median Std (Sigurjonson, 2001)': 'median_std',
                'Std (Sigurjonson, 2001)': 'std',
             },
             'value': 'mean'}
        scene_proxylit_method = pTypes.ListParameter(**p)
        scene_proxylit_method.sigValueChanged.connect(changeSplitMethod)

        self.sig_guard = False
        self.pushChild(scene_proxylit_method)
        self.pushChild(self.tile_size_max)
        self.pushChild(self.tile_size_min)
        self.pushChild(self.nan_allowed)
        self.pushChild(self.epsilon)
        self.pushChild(self.components)

    def onConfigUpdate(self):
        self.sig_guard = True
        for p in ['epsilon', 'nan_allowed',
                  'tile_size_min', 'tile_size_max']:
            param = getattr(self, p)
            param.setValue(getattr(self.sp.quadtree, p))
        self.sig_guard = False

    def updateEpsilonLimits(self):
        self.epsilon.setLimits((self.sp.quadtree.epsilon_limit,
                                2*self.sp.quadtree.epsilon))
