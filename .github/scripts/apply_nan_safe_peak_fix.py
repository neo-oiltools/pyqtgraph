from pathlib import Path

source_path = Path("pyqtgraph/graphicsItems/PlotDataItem.py")
source = source_path.read_text(encoding="utf-8")
start_marker = "            elif self.opts['downsampleMethod'] == 'peak':\n"
end_marker = "\n        if self.opts[\"dynamicRangeLimit\"] is not None and view_range is not None:\n"
start = source.find(start_marker)
end = source.find(end_marker, start)
if start < 0 or end < 0 or source.find(start_marker, start + 1) >= 0:
    raise RuntimeError("Could not identify a unique peak-downsampling block")

replacement = '''            elif self.opts['downsampleMethod'] == 'peak':
                # Use case: y is the monotonically increasing axis (time/depth),
                #           x is the signal/value (RPM, GR, etc.)
                finite = np.isfinite(x) & np.isfinite(y)

                if not finite.all():
                    # A non-finite sample represents a real line break. Reduce each
                    # finite run independently so downsampling can never reconnect
                    # across a time/depth discontinuity.
                    if connect is not None:
                        # Array-based connectivity has per-sample semantics. Keep the
                        # original data rather than changing those semantics implicitly.
                        pass
                    else:
                        output_x = []
                        output_y = []
                        index = 0
                        wrote_segment = False

                        while index < len(x):
                            while index < len(x) and not finite[index]:
                                index += 1
                            if index >= len(x):
                                break

                            segment_start = index
                            while index < len(x) and finite[index]:
                                index += 1

                            segment_x = x[segment_start:index]
                            segment_y = y[segment_start:index]
                            n = len(segment_y) // ds

                            if n > 0:
                                x2 = segment_x[:n * ds].reshape((n, ds))
                                y2 = segment_y[:n * ds].reshape((n, ds))
                                rows = np.arange(n)
                                min_indices = np.argmin(x2, axis=1)
                                max_indices = np.argmax(x2, axis=1)
                                same_extreme = min_indices == max_indices
                                if np.any(same_extreme):
                                    max_indices = max_indices.copy()
                                    max_indices[same_extreme] = ds - 1
                                first_indices = np.minimum(min_indices, max_indices)
                                second_indices = np.maximum(min_indices, max_indices)

                                reduced_x = np.empty((n, 2), dtype=x.dtype)
                                reduced_y = np.empty((n, 2), dtype=y.dtype)
                                reduced_x[:, 0] = x2[rows, first_indices]
                                reduced_x[:, 1] = x2[rows, second_indices]
                                reduced_y[:, 0] = y2[rows, first_indices]
                                reduced_y[:, 1] = y2[rows, second_indices]
                                segment_output_x = [reduced_x.reshape(n * 2)]
                                segment_output_y = [reduced_y.reshape(n * 2)]
                            else:
                                segment_output_x = []
                                segment_output_y = []

                            remainder_start = n * ds
                            if remainder_start < len(segment_x):
                                remainder_x = segment_x[remainder_start:]
                                remainder_y = segment_y[remainder_start:]
                                if len(remainder_x) <= 2:
                                    segment_output_x.append(remainder_x)
                                    segment_output_y.append(remainder_y)
                                else:
                                    min_index = int(np.argmin(remainder_x))
                                    max_index = int(np.argmax(remainder_x))
                                    if min_index == max_index:
                                        selected = np.array([0, len(remainder_x) - 1])
                                    else:
                                        selected = np.array(sorted((min_index, max_index)))
                                    segment_output_x.append(remainder_x[selected])
                                    segment_output_y.append(remainder_y[selected])

                            if segment_output_x:
                                if wrote_segment:
                                    output_x.append(np.array([np.nan]))
                                    output_y.append(np.array([np.nan]))
                                output_x.extend(segment_output_x)
                                output_y.extend(segment_output_y)
                                wrote_segment = True

                        if output_x:
                            x = np.concatenate(output_x)
                            y = np.concatenate(output_y)
                else:
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
source_path.write_text(source[:start] + replacement + source[end:], encoding="utf-8")

tests_path = Path("tests/graphicsItems/test_PlotDataItem.py")
tests = tests_path.read_text(encoding="utf-8")
marker = "def test_peak_downsampling_preserves_nan_discontinuities():"
if marker in tests:
    raise RuntimeError("NaN discontinuity regression test already exists")
tests += '''\n\ndef test_peak_downsampling_preserves_nan_discontinuities():\n    x = np.array([1.0, 4.0, 2.0, np.nan, 3.0, 9.0, 5.0])\n    y = np.array([1.0, 2.0, 3.0, np.nan, 10.0, 11.0, 12.0])\n    pdi = pg.PlotDataItem(x=x, y=y, connect=\"finite\")\n\n    pdi.setDownsampling(ds=3, method=\"peak\")\n    x_display, y_display = pdi.getData()\n\n    assert np.isnan(x_display).sum() == 1\n    assert np.isnan(y_display).sum() == 1\n    assert 4.0 in x_display\n    assert 9.0 in x_display\n    assert 2.0 in y_display\n    assert 11.0 in y_display\n'''
tests_path.write_text(tests, encoding="utf-8")
