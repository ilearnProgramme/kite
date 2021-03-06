#!/usr/bin/python2
from __future__ import division, absolute_import, print_function, \
    unicode_literals

from PySide import QtCore
from os import path
import time
import numpy as num
import pyqtgraph as pg
import pyqtgraph.parametertree.parameterTypes as pTypes

from pyqtgraph import dockarea
from ..qt_utils import _viridis_data
from ..meta import calcPrecission, formatScalar

__all__ = ['KiteView', 'KitePlot', 'KiteToolColormap',
           'KiteParameterGroup']


def get_resource(filename):
    return path.join(path.dirname(path.realpath(__file__)), 'res', filename)


class KiteView(dockarea.DockArea):
    def __init__(self):
        dockarea.DockArea.__init__(self)
        self.tool_docks = []

        dock_main = dockarea.Dock(
            self.title,
            autoOrientation=False,
            widget=self.main_widget)
        dock_colormap = dockarea.Dock(
            'Colormap',
            autoOrientation=False,
            widget=KiteToolColormap(self.main_widget))
        dock_colormap.setStretch(1, None)

        for i, (name, tool) in enumerate(self.tools.iteritems()):
            self.tool_docks.append(
                dockarea.Dock(
                    name,
                    widget=tool,
                    size=(2, 2),
                    autoOrientation=False))
            self.addDock(self.tool_docks[-1], position='bottom')

        self.addDock(dock_main, position='left')
        self.addDock(dock_colormap, position='right')


class LOSArrow(pg.GraphicsWidget, pg.GraphicsWidgetAnchor):

    def __init__(self, model):
        pg.GraphicsWidget.__init__(self)
        pg.GraphicsWidgetAnchor.__init__(self)

        self.model = model

        self.arrow = pg.ArrowItem(
            parent=self,
            angle=0.,
            brush=(0, 0, 0, 180),
            pen=(255, 255, 255),
            pxMode=True)
        self.orientArrow()

        self.model.sigSceneChanged.connect(self.orientArrow)
        self.setFlag(self.ItemIgnoresTransformations)

    @QtCore.Slot()
    def orientArrow(self):
        phi = num.median(self.model.scene.phi)
        theta = num.median(self.model.scene.theta)

        angle = -num.rad2deg(phi)
        theta_f = theta / (num.pi/2)

        tipAngle = 30. + theta_f * 20.
        tailLen = 15 + theta_f * 15.

        self.arrow.setStyle(
            angle=angle,
            tipAngle=tipAngle,
            tailLen=tailLen,
            tailWidth=6,
            headLen=25)
        self.arrow.setRotation(self.arrow.opts['angle'])

    def setParentItem(self, parent):
        pg.GraphicsWidget.setParentItem(self, parent)

    def boundingRect(self):
        return QtCore.QRectF(0, 0, self.width(), self.height())


class KitePlot(pg.PlotWidget):

    def __init__(self, model, los_arrow=False):
        pg.PlotWidget.__init__(self)
        self.model = model
        self.draw_time = 0.
        self._data = None

        border_pen = pg.mkPen(255, 255, 255, 50)
        self.image = pg.ImageItem(
            None,
            autoDownsample=False,
            border=border_pen,
            useOpenGL=True)

        self.setAspectLocked(True)
        self.plotItem.getAxis('left').setZValue(100)
        self.plotItem.getAxis('bottom').setZValue(100)
        self.setLabels(
            bottom=('Easting', 'm'),
            left=('Northing', 'm'))

        self.hint = {
            'east': 0.,
            'north': 0.,
            'value': num.nan,
            'measure': self.component.title(),
            'vlength': '03',
            'precision': '3',
        }

        self.hint_text = pg.LabelItem(
            text='',
            justify='right', size='8pt',
            parent=self.plotItem)
        self.hint_text.anchor(
            itemPos=(1., 0.),
            parentPos=(1., 0.))
        self.hint_text.text_template =\
            '<span style="font-family: monospace; color: #fff;'\
            'background-color: #000;">'\
            'East {east:08.2f} m | North {north:08.2f} m | '\
            '{measure} {value:{length}.{precision}f}</span>'
        self.hint_text.setOpacity(.6)

        self.addItem(self.image)
        self.update()

        self.transFromFrame()
        self._move_sig = pg.SignalProxy(
            self.image.scene().sigMouseMoved,
            rateLimit=25, slot=self.mouseMoved)

        if los_arrow:
            self.addLOSArrow()

        # self.addIsocurve()
        # self.scalebar()

    def addLOSArrow(self):
        self.los_arrow = LOSArrow(self.model)
        self.los_arrow.setParentItem(self.graphicsItem())
        self.los_arrow.anchor(
            itemPos=(1., 0.), parentPos=(1, 0.),
            offset=(-10., 40.))

    def transFromFrame(self):
        self.image.resetTransform()
        self.image.scale(self.model.frame.dE, self.model.frame.dN)

    def scalebar(self):
        ''' Not working '''
        self.scale_bar = pg.ScaleBar(
            10,
            width=5,
            suffix='m')
        self.scale_bar.setParentItem(self.plotItem)
        self.scale_bar.anchor((1, 1), (1, 1), offset=(-20, -20))

    @property
    def component(self):
        return self._component

    @component.setter
    def component(self, component):
        if component not in self.components_available.keys():
            raise AttributeError('Invalid component %s' % component)
        self._component = component
        self.update()

    @property
    def data(self):
        if self._data is None:
            self._data = self.components_available[self.component][1](
                self.model)
        return self._data
        # return self._data  # num.nan_to_num(_data)

    @QtCore.Slot()
    def update(self):
        self._data = None
        ts = time.time()

        self.image.updateImage(self.data.T)
        self.draw_time = time.time() - ts

        self.hint['precision'], self.hint['vlength'] =\
            calcPrecission(self.data)
        self.mouseMoved()
        # self.addIsocurves()

    def addIsocurve(self, level=0.):
        iso = pg.IsocurveItem(level=level, pen='g')
        iso.setZValue(1000)
        iso.setData(pg.gaussianFilter(self.data, (5, 5)))
        iso.setParentItem(self.image)

        self.iso = iso

    @QtCore.Slot(object)
    def mouseMoved(self, event=None):
        if event is None:
            return
        elif self.image.sceneBoundingRect().contains(event[0]):
            map_pos = self.plotItem.vb.mapSceneToView(event[0])
            if not map_pos.isNull():
                img_pos = self.image.mapFromScene(event).data
                value = self.image.image[int(img_pos().x()),
                                         int(img_pos().y())]

                self.hint['east'] = map_pos.x()
                self.hint['north'] = map_pos.y()
                self.hint['value'] = value
        self.hint['length'] = '03' if num.isnan(self.hint['value'])\
                              else self.hint['vlength']
        self.hint_text.setText(
            self.hint_text.text_template.format(**self.hint))


class KiteToolColormap(pg.HistogramLUTWidget):
    def __init__(self, plot):
        pg.HistogramLUTWidget.__init__(self, image=plot.image)
        self._plot = plot

        zero_marker = pg.InfiniteLine(
            pos=0,
            angle=0,
            pen='w',
            movable=False)
        zero_marker.setValue(0.)
        zero_marker.setZValue(1000)
        self.vb.addItem(zero_marker)

        self.axis.setLabel('Displacement / m')
        # self.plot.rotate(-90)
        # self.layout.rotate(90)
        # self.gradient.setOrientation('bottom')
        self.setSymColormap()
        self._plot.image.sigImageChanged.connect(self.imageChanged)
        # self.isoCurveControl()

    def imageChanged(self):
        if self._plot.component == 'weight':
            self.setQualitativeColormap()
        else:
            self.setSymColormap()

    def setSymColormap(self):
        cmap = {'ticks':
                [[0., (0, 0, 0, 255)],
                 [1e-3, (106, 0, 31, 255)],
                 [.5, (255, 255, 255, 255)],
                 [1., (8, 54, 104, 255)]],
                'mode': 'rgb'}
        cmap = {'ticks':
                [[0., (0, 0, 0)],
                 [1e-3, (172, 56, 56)],
                 [.5, (255, 255, 255)],
                 [1., (51, 53, 120)]],
                'mode': 'rgb'}
        lvl_min = num.nanmin(self._plot.data)
        lvl_max = num.nanmax(self._plot.data)
        abs_range = max(abs(lvl_min), abs(lvl_max))

        self.gradient.restoreState(cmap)
        self.setLevels(-abs_range, abs_range)

    def setQualitativeColormap(self):
        l = len(_viridis_data) - 1
        cmap = {'mode': 'rgb'}
        cmap['ticks'] = [[float(i)/l, c] for i, c in enumerate(_viridis_data)]
        self.gradient.restoreState(cmap)
        self.setLevels(num.nanmin(self._plot.data),
                       num.nanmax(self._plot.data))

    def isoCurveControl(self):
        iso_ctrl = pg.InfiniteLine(
            pos=0,
            angle=0,
            pen='g',
            movable=True)
        iso_ctrl.setValue(0.)
        iso_ctrl.setZValue(1000)

        def isolineChange():
            self._plot.iso.setLevel(iso_ctrl.value())

        iso_ctrl.sigDragged.connect(isolineChange)
        self.vb.addItem(iso_ctrl)


class KiteParameterGroup(pTypes.GroupParameter):
    def __init__(self, model, model_attr=None, **kwargs):
        self.model = model
        self.model_attr = model_attr

        if isinstance(self.parameters, list):
            self.parameters = dict.fromkeys(self.parameters)

        pTypes.GroupParameter.__init__(self, **kwargs)
        self.updateValues()

    def updateValues(self):
        if not hasattr(self, 'parameters'):
            return

        if self.model_attr is not None and\
           hasattr(self.model, self.model_attr):
            model = getattr(self.model, self.model_attr)
        else:
            model = self.model

        for param, f in self.parameters.iteritems():
            QtCore.QCoreApplication.processEvents()
            try:
                if callable(f):
                    value = f(model)
                    # print('Updating %s: %s (func)' % (param, value))
                else:
                    value = getattr(model, param)
                    # print('Updating %s: %s (getattr)' % (param, value))
                try:
                    value = formatScalar(float(value))
                except ValueError:
                    pass
            except AttributeError:
                value = 'n/a'
            try:
                self.child(param).setValue(value)
            except Exception:
                self.addChild({'name': param,
                               'value': value,
                               'type': 'str',
                               'readonly': True})

    def pushChild(self, child, **kwargs):
        self.insertChild(0, child, **kwargs)
