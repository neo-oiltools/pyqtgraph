from pathlib import Path

source_path = Path("pyqtgraph/graphicsItems/PlotDataItem.py")
source = source_path.read_text(encoding="utf-8")

old = '''            elif self.opts['downsampleMethod'] == 'peak':
                # Use case: y is the monotonically increasing axis (time/depth),
                #           x is the signal/value (RPM, GR, etc.)
                n = len(y) // ds
                if n < 1:
                    # Nothing to downsample safely
                    pass
                else:
                    # Representative y per bin (try to be centered)
                    y1 = np.empty((n, 2), dtype=y.dtype)
                    sty = ds // 2
                    y_center = y[sty:sty + n * ds:ds]
                    y1[:, 0] = y_center
                    y1[:, 1] = y_center
                    y = y1.reshape(n * 2)

                    # Peaks/valleys of x per bin
                    x1 = np.empty((n, 2), dtype=x.dtype)
                    x2 = x[:n * ds].reshape((n, ds))

                    # If your data can contain NaNs, prefer nanmax/nanmin:
                    # x1[:, 0] = np.nanmax(x2, axis=1)
                    # x1[:, 1] = np.nanmin(x2, axis=1)
                    x1[:, 0] = x2.max(axis=1)
                    x1[:, 1] = x2.min(axis=1)

                    x = x1.reshape(n * 2)

                    if connect is not None:
                        # Keep segment connectivity consistent: only keep "connected"
                        # if all original samples in the bin were connected.
                        c = np.ones((n * 2), dtype=bool)
                        c[1::2] = connect[:n * ds].reshape(n, ds).all(axis=1)
                        connect = c
'''

new = '''            elif self.opts['downsampleMethod'] == 'peak':
                # Use case: y is the monotonically increasing axis (time/depth),
                #           x is the signal/value (RPM, GR, etc.)
                n = len(y) // ds
                if n < 1:
                    # Nothing to downsample safely
                    pass
                else:
                    x2 = x[:n * ds].reshape((n, ds))
                    y2 = y[:n * ds].reshape((n, ds))
                    rows = np.arange(n)

                    min_indices = np.argmin(x2, axis=1)
                    max_indices = np.argmax(x2, axis=1)

                    # For a constant bucket argmin and argmax point at the same
                    # sample. Keep the bucket endpoints so its time/depth extent
                    # remains represented.
                    same_extreme = min_indices == max_indices
                    if np.any(same_extreme):
                        max_indices = max_indices.copy()
                        max_indices[same_extreme] = ds - 1

                    # Emit extrema in source order, with the y coordinate of the
                    # original samples at which they occurred.
                    first_indices = np.minimum(min_indices, max_indices)
                    second_indices = np.maximum(min_indices, max_indices)

                    x1 = np.empty((n, 2), dtype=x.dtype)
                    y1 = np.empty((n, 2), dtype=y.dtype)
                    x1[:, 0] = x2[rows, first_indices]
                    x1[:, 1] = x2[rows, second_indices]
                    y1[:, 0] = y2[rows, first_indices]
                    y1[:, 1] = y2[rows, second_indices]

                    x = x1.reshape(n * 2)
                    y = y1.reshape(n * 2)

                    if connect is not None:
                        # Keep segment connectivity consistent: only keep "connected"
                        # if all original samples in the bin were connected.
                        c = np.ones((n * 2), dtype=bool)
                        c[1::2] = connect[:n * ds].reshape(n, ds).all(axis=1)
                        connect = c
'''

occurrences = source.count(old)
if occurrences != 1:
    raise RuntimeError(f"Expected the peak block exactly once, found {occurrences} occurrences")
source_path.write_text(source.replace(old, new), encoding="utf-8")

tests_path = Path("tests/graphicsItems/test_PlotDataItem.py")
tests = tests_path.read_text(encoding="utf-8")
marker = "def test_peak_downsampling_preserves_extrema_positions():"
if marker in tests:
    raise RuntimeError("Peak-position regression test already exists")

tests += '''\n\ndef test_peak_downsampling_preserves_extrema_positions():\n    x = np.array([5.0, 6.0, 50.0, 4.0, 3.0, 5.0])\n    y = np.arange(1000.0, 1006.0)\n    pdi = pg.PlotDataItem(x=x, y=y)\n\n    pdi.setDownsampling(ds=6, method=\"peak\")\n    x_display, y_display = pdi.getData()\n\n    np.testing.assert_array_equal(x_display, [50.0, 3.0])\n    np.testing.assert_array_equal(y_display, [1002.0, 1004.0])\n\n\ndef test_peak_downsampling_preserves_constant_bucket_extent():\n    x = np.array([7.0, 7.0, 7.0, 7.0])\n    y = np.arange(4.0)\n    pdi = pg.PlotDataItem(x=x, y=y)\n\n    pdi.setDownsampling(ds=4, method=\"peak\")\n    x_display, y_display = pdi.getData()\n\n    np.testing.assert_array_equal(x_display, [7.0, 7.0])\n    np.testing.assert_array_equal(y_display, [0.0, 3.0])\n'''
tests_path.write_text(tests, encoding="utf-8")
