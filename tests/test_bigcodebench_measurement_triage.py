from scripts.triage_bigcodebench_measurement_v1 import classify


def row(libs, source, test):
    return dict(task_id='BigCodeBench/mock',libs=repr(libs),canonical_solution=source,
                test=test,complete_prompt='prompt')


def test_native_plot_without_value_marker_is_only_flagged_not_admitted():
    item=classify(row(['matplotlib','pandas'],'ax.plot([1],[2])','self.assertIsNotNone(ax)'))
    assert item['flags']['native_object_library']
    assert item['flags']['plot_library']
    assert not item['flags']['test_plot_values_static']
    assert 'admission' not in item


def test_network_and_file_markers_overlap_without_claiming_execution():
    item=classify(row(['requests','json'],'with open(path) as f: pass','mock_requests()'))
    assert item['flags']['network_library'] and item['flags']['reference_file_io_static']
    assert not item['flags']['web_framework']
