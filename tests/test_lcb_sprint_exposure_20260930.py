import unittest
from scripts import build_lcb_sprint_exposure_20260930 as exposure


class HistoricalExposureTests(unittest.TestCase):
    def test_nonfinite_score_does_not_invalidate_valid_root(self):
        audit={'nonfinite_scalar_tokens_ignored':0,'malformed_nonfinite_identity_fields':0,
               'valid_scalar_identity_fields':0}
        value=exposure.historical_json('{"root":"atcoder:abc325_a","score":NaN}',audit)
        exposure.identity_shape_audit(value,audit)
        self.assertEqual(value['root'],'atcoder:abc325_a')
        self.assertEqual(audit['valid_scalar_identity_fields'],1)
        self.assertEqual(audit['malformed_nonfinite_identity_fields'],0)
        self.assertEqual(audit['nonfinite_scalar_tokens_ignored'],1)

    def test_nonfinite_identity_is_explicitly_malformed(self):
        audit={'nonfinite_scalar_tokens_ignored':0,'malformed_nonfinite_identity_fields':0,
               'valid_scalar_identity_fields':0}
        value=exposure.historical_json('{"root":NaN}',audit)
        exposure.identity_shape_audit(value,audit)
        self.assertEqual(audit['malformed_nonfinite_identity_fields'],1)

    def test_duplicate_identity_not_silently_overwritten(self):
        audit={'nonfinite_scalar_tokens_ignored':0}
        with self.assertRaises(exposure.bundle.inquiry.InstrumentError):
            exposure.historical_json('{"root":"a","root":"b"}',audit)

    def test_labels_and_model_text_excluded_from_shape_walk(self):
        audit={'malformed_nonfinite_identity_fields':0,'valid_scalar_identity_fields':0}
        exposure.identity_shape_audit({'labels':[{'root':'secret'}],
            'outputs':[{'root':'secret'}],'root':'safe'},audit)
        self.assertEqual(audit['valid_scalar_identity_fields'],1)


if __name__=='__main__': unittest.main()
