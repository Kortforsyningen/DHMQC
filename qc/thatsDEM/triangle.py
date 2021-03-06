from __future__ import print_function
# Copyright (c) 2015, Danish Geodata Agency <gst@gst.dk>
# Copyright (c) 2018, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
from builtins import object
import sys
import os
import ctypes
import time
import numpy as np
LIBDIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "lib"))

LIBNAME = "libtripy"
DELAUNATOR_LIBNAME = "libdelaunator"
#'64' not appended to libname anymore
if sys.platform.startswith("win"):
    LIBNAME += ".dll"
    DELAUNATOR_LIBNAME += ".dll"
    os.environ["PATH"] += ";" + LIBDIR
elif "darwin" in sys.platform:
    LIBNAME += ".dylib"
    DELAUNATOR_LIBNAME += ".dylib"
else:
    LIBNAME += ".so"
    DELAUNATOR_LIBNAME += ".so"
LP_CDOUBLE = ctypes.POINTER(ctypes.c_double)
LP_CFLOAT = ctypes.POINTER(ctypes.c_float)
LP_CINT = ctypes.POINTER(ctypes.c_int)
LP_CCHAR = ctypes.POINTER(ctypes.c_char)
LP_CULONGLONG = ctypes.POINTER(ctypes.c_ulonglong)
# lib_name=os.path.join(os.path.dirname(__file__),LIBNAME)
lib_name = os.path.join(LIBDIR, LIBNAME)
delaunator_lib_name = os.path.join(LIBDIR, DELAUNATOR_LIBNAME)
# Load library directly via ctypes. Could also have used the numpy interface.
lib = ctypes.cdll.LoadLibrary(lib_name)
delaunator_lib = ctypes.cdll.LoadLibrary(delaunator_lib_name)
# Args and return types of c functions. Corresponds to a header file.
lib.free_index.restype = None
lib.free_index.argtypes = [ctypes.c_void_p]
lib.find_triangle.restype = None
lib.find_triangle.argtypes = [
    LP_CDOUBLE,
    LP_CINT,
    LP_CDOUBLE,
    LP_CINT,
    ctypes.c_void_p,
    LP_CCHAR,
    ctypes.c_int]
# void find_appropriate_triangles(double *pts, int *out, double *base_pts,
# double *base_z, int *tri, spatial_index *ind, int np, double tol_xy,
# double tol_z);
lib.inspect_index.restype = None
lib.inspect_index.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
lib.build_index.restype = ctypes.c_void_p
lib.build_index.argtypes = [LP_CDOUBLE, LP_CINT, ctypes.c_double, ctypes.c_int, ctypes.c_int]
# interpolate2(double *pts, double *base_pts, double *base_z, double *out,
# int *tri, spatial_index *ind, int np)
lib.interpolate.argtypes = [
    LP_CDOUBLE,
    LP_CDOUBLE,
    LP_CDOUBLE,
    LP_CDOUBLE,
    ctypes.c_double,
    LP_CINT,
    ctypes.c_void_p,
    LP_CCHAR,
    ctypes.c_int]
lib.interpolate.restype = None
# void make_grid(double *base_pts,double *base_z, int *tri, float *grid,
# float tgrid, double nd_val, int ncols, int nrows, double cx, double cy,
# double xl, double yu, spatial_index *ind)
lib.make_grid.argtypes = [LP_CDOUBLE,
                          LP_CDOUBLE,
                          LP_CINT,
                          LP_CFLOAT,
                          LP_CFLOAT,
                          ctypes.c_float,
                          ctypes.c_int,
                          ctypes.c_int] + [ctypes.c_double] * 4 + [ctypes.c_void_p]
lib.make_grid.restype = None
# void make_grid_low(double *base_pts,double *base_z, int *tri, float
# *grid,  float nd_val, int ncols, int nrows, double cx, double cy, double
# xl, double yu, double cut_off, spatial_index *ind)
lib.make_grid_low.argtypes = [LP_CDOUBLE,
                              LP_CDOUBLE,
                              LP_CINT,
                              LP_CFLOAT,
                              ctypes.c_float,
                              ctypes.c_int,
                              ctypes.c_int] + [ctypes.c_double] * 5 + [ctypes.c_void_p]
lib.make_grid_low.restype = None
lib.optimize_index.argtypes = [ctypes.c_void_p]
lib.optimize_index.restype = None

delaunator_lib.triangulate.argtypes = [ctypes.c_int, LP_CDOUBLE, LP_CINT, ctypes.POINTER(LP_CINT)]
delaunator_lib.triangulate.restype = None
delaunator_lib.free_face_data.argtypes = [ctypes.POINTER(LP_CINT)]
delaunator_lib.free_face_data.restype = None


class TriangulationBase(object):
    """Triangulation class inspired by scipy.spatial.Delaunay
    Uses Triangle to do the hard work. Automatically builds an index.
    """
    vertices = None
    index = None
    points = None
    segments = None
    holes = None
    ntrig = None
    transform = None  # can be used to speed up things even more....

    def __del__(self):
        """Destructor"""
        if self.vertices is not None:
            delaunator_lib.free_face_data(ctypes.byref(self.ptr_faces))
        if self.index is not None:
            lib.free_index(self.index)

    def validate_points(self, points, ndim=2, dtype=np.float64):
        # ALL this stuff is not needed if we use numpys ctypeslib interface - TODO.
        if not isinstance(points, np.ndarray):
            raise ValueError("Input points must be a Numpy ndarray")
        ok = points.flags["ALIGNED"] and points.flags[
            "C_CONTIGUOUS"] and points.flags["OWNDATA"] and points.dtype == dtype
        if (not ok):
            raise ValueError(
                "Input points must have flags 'ALIGNED','C_CONTIGUOUS','OWNDATA' and data type %s" %
                dtype)
        # TODO: figure out something useful here....
        if points.ndim != ndim or (ndim == 2 and points.shape[1] != 2):
            raise ValueError("Bad shape of input - points:(n,2) z: (n,), indices: (n,)")

    def interpolate(self, z_base, xy_in, nd_val=-999, mask=None):
        """Barycentric interpolation of input points xy_in based on values z_base in vertices. Points outside triangulation gets nd_val"""
        self.validate_points(xy_in)
        self.validate_points(z_base, 1)
        if z_base.shape[0] != self.points.shape[0]:
            raise ValueError(
                "There must be exactly the same number of input zs as the number of triangulated points.")
        if mask is not None:
            if mask.shape[0] != self.ntrig:
                raise ValueError("Validity mask size differs from number of triangles")
            self.validate_points(mask, ndim=1, dtype=np.bool)
            pmask = mask.ctypes.data_as(LP_CCHAR)
        else:
            pmask = None
        out = np.empty((xy_in.shape[0],), dtype=np.float64)
        lib.interpolate(xy_in.ctypes.data_as(LP_CDOUBLE), self.points.ctypes.data_as(LP_CDOUBLE), z_base.ctypes.data_as(LP_CDOUBLE),
                        out.ctypes.data_as(LP_CDOUBLE), nd_val, self.vertices, self.index, pmask, xy_in.shape[0])
        return out

    def make_grid(self, z_base, ncols, nrows, xl, cx, yu, cy, nd_val=-999, return_triangles=False):
        """
        Interpolate a grid using (barycentric) interpolation.
        Args:
            z_base: The values to interpolate (numpy 1d array, float64).
            ncols: number of columns.
            nrows: number of rows.
            xl: Left edge / corner (GDAL style).
            cx: Horisontal cell size.
            yu: Upper edge / corner (GDAL style).
            cy: Vertical cell size (positive).
            nd_val: output no data value.
            return_triangles: bool, if True also return a grid containing triangle bounding box sizes.
        Returns:
            Numpy 2d-arrray (float64) (and numpy 2d float32 array if return_triangles=True)
        """
        # void make_grid(double *base_pts,double *base_z, int *tri, double *grid,
        # double nd_val, int ncols, int nrows, double cx, double cy, double xl,
        # double yu, spatial_index *ind)
        if z_base.shape[0] != self.points.shape[0]:
            raise ValueError(
                "There must be exactly the same number of input zs as the number of triangulated points.")
        grid = np.empty((nrows, ncols), dtype=np.float32)
        if return_triangles:
            t_grid = np.zeros((nrows, ncols), dtype=np.float32)
            p_t_grid = t_grid.ctypes.data_as(LP_CFLOAT)
        else:
            p_t_grid = None
        lib.make_grid(
            self.points.ctypes.data_as(LP_CDOUBLE),
            z_base.ctypes.data_as(LP_CDOUBLE),
            self.vertices,
            grid.ctypes.data_as(LP_CFLOAT),
            p_t_grid,
            nd_val,
            ncols,
            nrows,
            cx,
            cy,
            xl,
            yu,
            self.index)
        if return_triangles:
            return grid, t_grid
        else:
            return grid

    def make_grid_low(self, z_base, ncols, nrows, xl, cx, yu, cy, nd_val=-999, cut_off=1.5):
        """Experimental: gridding avoiding steep edges"""
        # void make_grid(double *base_pts,double *base_z, int *tri, double *grid,
        # double nd_val, int ncols, int nrows, double cx, double cy, double xl,
        # double yu, spatial_index *ind)
        if z_base.shape[0] != self.points.shape[0]:
            raise ValueError(
                "There must be exactly the same number of input zs as the number of triangulated points.")
        grid = np.empty((nrows, ncols), dtype=np.float32)
        lib.make_grid_low(
            self.points.ctypes.data_as(LP_CDOUBLE),
            z_base.ctypes.data_as(LP_CDOUBLE),
            self.vertices,
            grid.ctypes.data_as(LP_CFLOAT),
            nd_val,
            ncols,
            nrows,
            cx,
            cy,
            xl,
            yu,
            cut_off,
            self.index)
        return grid

    def get_triangles(self, indices=None):
        """Copy allocated triangles to numpy (n,3) int32 array.

        Invalid indices used to give (-1,-1,-1) rows, will now cause an
        exception."""
        if indices is None:
            indices = np.arange(0, self.ntrig).astype(np.int32)
        self.validate_points(indices, 1, np.int32)
        vertex_indices_array = np.ctypeslib.as_array(self.ptr_faces, (self.ntrig, 3))
        out = vertex_indices_array[indices, :].astype(np.int32)
        return out

    def get_triangle_centers(self):
        """
        Calculate triangle center of masses.
        Returns:
            Numpy 2d array of shape (ntriangles,2)
        """
        indices_array = np.ctypeslib.as_array(self.ptr_faces, (self.ntrig, 3))
        triangles_x = self.points[indices_array.ravel(), 0].reshape(-1, 3)
        triangles_y = self.points[indices_array.ravel(), 1].reshape(-1, 3)
        out = np.column_stack([np.sum(triangles_x, axis=1) / 3.0, np.sum(triangles_y, axis=1) / 3.0]).astype(np.float64)
        return out

    def rebuild_index(self, cs):
        """Rebuild index with another cell size"""
        lib.free_index(self.index)
        self.index = lib.build_index(
            self.points.ctypes.data_as(LP_CDOUBLE),
            self.vertices,
            cs,
            self.points.shape[0],
            self.ntrig)

    def optimize_index(self):
        """Only shrinks index slightly in memory. Should also sort index after areas of intersections between cells and triangles..."""
        lib.optimize_index(self.index)

    def inspect_index(self):
        """Return info as text"""
        info = ctypes.create_string_buffer(1024)
        lib.inspect_index(self.index, info, 1024)
        return info.value

    def find_triangles(self, xy, mask=None):
        """
        Finds triangle indices of input points. Returns -1 if no triangles is found.
        Can be used to implement a point in polygon algorithm (for convex polygons without holes).
        Args:
            xy: The points in which to look for containing triangles.
            mask: optional, A 1d validity mask marking validity of triangles.
        Returns:
            Numpy 1d int32 array containing triangles indices. -1 is used to indicate no (valid) triangle.
        """
        self.validate_points(xy)
        out = np.empty((xy.shape[0],), dtype=np.int32)
        if mask is not None:
            if mask.shape[0] != self.ntrig:
                raise ValueError("Validity mask size differs from number of triangles")
            self.validate_points(mask, ndim=1, dtype=np.bool)
            pmask = mask.ctypes.data_as(LP_CCHAR)
        else:
            pmask = None
        lib.find_triangle(
            xy.ctypes.data_as(LP_CDOUBLE),
            out.ctypes.data_as(LP_CINT),
            self.points.ctypes.data_as(LP_CDOUBLE),
            self.vertices,
            self.index,
            pmask,
            xy.shape[0])
        return out


class Triangulation(TriangulationBase):
    """TriangulationBase implementation. Will construct a triangulation and an index of triangles."""

    def __init__(self, points, cs=-1):
        self.validate_points(points)
        self.points = points
        num_faces = ctypes.c_int(0)
        self.ptr_faces = ctypes.POINTER(ctypes.c_int)()
        delaunator_lib.triangulate(points.shape[0],
                                   points.ctypes.data_as(LP_CDOUBLE),
                                   ctypes.byref(num_faces),
                                   ctypes.byref(self.ptr_faces))
        self.ntrig = num_faces.value
        self.vertices = self.ptr_faces.contents
        #print("Triangles: %d" %self.ntrig)
        t1 = time.process_time()
        self.index = lib.build_index(
            points.ctypes.data_as(LP_CDOUBLE),
            self.vertices,
            cs,
            points.shape[0],
            self.ntrig)
        if self.index is None:
            raise Exception("Failed to build index...")
        t2 = time.process_time()


def unit_test(n1=1000, n2=1000):
    # Test that things work. Call with number_of_vertices number_of_points_to_interpolate
    n1 = int(n1)
    n2 = int(n2)
    points = np.random.rand(n1, 2) * 1000.0
    z = np.random.rand(n1) * 100
    xmin, ymin = points.min(axis=0)
    xmax, ymax = points.max(axis=0)
    print("Span of 'pointcloud': %.2f,%.2f,%.2f,%.2f" % (xmin, ymin, xmax, ymax))
    dx = (xmax - xmin)
    dy = (ymax - ymin)
    cx, cy = points.mean(axis=0)
    xy = np.random.rand(n2, 2) * [dx, dy] * 0.3 + [cx, cy]
    t1 = time.process_time()
    tri = Triangulation(points, -1)
    t2 = time.process_time()
    t3 = t2 - t1
    print("Building triangulation and index of %d points: %.4f s" % (n1, t3))
    print(tri.inspect_index())
    t1 = time.process_time()
    tri.optimize_index()
    t2 = time.process_time()
    t3 = t2 - t1
    print("\n%s\nOptimizing index: %.4fs" % ("*" * 50, t3))
    print(tri.inspect_index())
    t1 = time.process_time()
    T = tri.find_triangles(xy)
    t2 = time.process_time()
    t3 = t2 - t1
    print("Finding %d simplices: %.4f s, pr. 1e6: %.4f s" % (n2, t3, t3 / n2 * 1e6))
    assert T.min() >= 0
    assert T.max() < tri.ntrig
    t1 = time.process_time()
    zi = tri.interpolate(z, points)
    t2 = time.process_time()
    t3 = t2 - t1
    print("Interpolation test of vertices:  %.4f s, pr. 1e6: %.4f s" % (t3, t3 / n1 * 1e6))
    D = np.fabs(z - zi)
    print("Diff: %.15g, %.15g, %.15g" % (D.max(), D.min(), D.mean()))
    assert(D.max() < 1e-4)


if __name__ == "__main__":
    unit_test()
