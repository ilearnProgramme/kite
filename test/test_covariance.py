#!/bin/python
import unittest
import numpy as num
from common import Benchmark
from kite import Scene, SceneTest
import matplotlib.pyplot as plt
import os

benchmark = Benchmark()


class TestCovariance(unittest.TestCase):

    def setUp(self):
        file = os.path.join(
         os.path.abspath(os.path.dirname(__file__)),
         'data/20110214_20110401_ml4_sm.unw.geo_ig_dsc_ionnocorr.mat')

        self.sc = Scene.import_data(file)
        self.sc.meta.scene_title = 'Matlab Input - Myanmar 2011-02-14'
        self.sc._log.setLevel('CRITICAL')

        # self.sc.quadtree.epsilon = .05
        # self.sc.quadtree.tile_size_limit = (250, 12e3)
        # self.sc = SceneTest.createGauss(ny=250)

    def __setUp(self):
        self.sc = SceneTest.createGauss()
        # self.sc._log.setLevel('CRITICAL')

    # @unittest.skip('Skipped')
    def testCovariance(self):
        cov = self.sc.covariance
        cov.epsilon = .02
        cov.subsampling = 24

        d = []
        d.append(('Full', cov._calcCovarianceMatrix(method='full',
                 nthreads=0)))
        d.append(('Focal', cov._calcCovarianceMatrix(method='focal')))

        for _, c1 in d:
            for _, c2 in d:
                num.testing.assert_allclose(c1, c2,
                                            rtol=200, atol=2e3, verbose=True)

    @benchmark
    @unittest.skip('Skip!')
    def testCovariancParallel(self):
        cov = self.sc.covariance
        cov._calcCovarianceMatrix(method='full', nthreads=12)

    @benchmark
    @unittest.skip('Skip!')
    def testCovariancSingle(self):
        cov = self.sc.covariance
        cov._calcCovarianceMatrix(method='full', nthreads=1)

    @benchmark
    @unittest.skip('Skip!')
    def testCovariancFocal(self):
        cov = self.sc.covariance
        cov._calcCovarianceMatrix(method='focal')

    @unittest.skip('Skip!')
    def testCovarianceVisual(self):
        cov = self.sc.covariance
        cov.epsilon = .02
        cov.subsampling = 10
        # l = self.sc.quadtree.leafs[0]
        d = []
        d.append(('Full', cov._calcCovarianceMatrix(method='full',
                 nthreads=0)))
        d.append(('Focal', cov._calcCovarianceMatrix(method='focal')))

        fig, _ = plt.subplots(1, len(d))
        for i, (title, mat) in enumerate(d):
            print '%s Max %f' % (title, num.nanmax(mat)), mat.shape
            fig.axes[i].imshow(mat)
            fig.axes[i].set_title(title)
        plt.show()


if __name__ == '__main__':
    unittest.main(exit=False)
    print benchmark
