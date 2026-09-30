import io
import json
from pathlib import Path
import tempfile
import unittest
from fractions import Fraction

from scripts import build_lcb_sprint_bundle_20260930 as bundle


class LcbSprintBundleTests(unittest.TestCase):
    def test_ascii_tokens_preserve_nonascii_whitespace_and_order(self):
        self.assertEqual(bundle.normalize('  1\t2\r\n',bundle.ASCII_TOKENS),(b'1',b'2'))
        self.assertNotEqual(bundle.normalize('1\u00a02',bundle.ASCII_TOKENS),(b'1',b'2'))
        self.assertNotEqual(bundle.normalized_hash('1 2',bundle.ASCII_TOKENS),
                            bundle.normalized_hash('2 1',bundle.ASCII_TOKENS))
        self.assertEqual(bundle.normalized_hash('1 2\n',bundle.ASCII_TOKENS),
                         bundle.normalized_hash('1\t2',bundle.ASCII_TOKENS))

    def test_single_line_retains_required_literal_space(self):
        self.assertEqual(bundle.normalize('Aoki san\r\n',bundle.SINGLE_LINE),(b'Aoki san',))
        self.assertNotEqual(bundle.normalize('Aoki  san\n',bundle.SINGLE_LINE),
                            bundle.normalize('Aoki san\n',bundle.SINGLE_LINE))
        self.assertNotEqual(bundle.normalize('Aoki san \n',bundle.SINGLE_LINE),
                            bundle.normalize('Aoki san\n',bundle.SINGLE_LINE))
        for value in ('Aoki san\n\n','Aoki\nsan','Aoki san\r'):
            with self.assertRaises(bundle.BundleError): bundle.normalize(value,bundle.SINGLE_LINE)

    def test_component_split_is_complete_outcome_blind_and_balanced(self):
        nodes=[{'node_id':'r'+str(i),'operational_component':'c'+str(i//2)} for i in range(20)]
        eligible={n['node_id'] for n in nodes}
        roots,components,counts=bundle.split_components(nodes,eligible)
        roots2,components2,counts2=bundle.split_components(list(reversed(nodes)),eligible)
        self.assertEqual((roots,components,counts),(roots2,components2,counts2))
        self.assertEqual(counts,{'development':6,'tuning':2,'evaluation':2})
        for i in range(0,20,2): self.assertEqual(roots['r'+str(i)]['split'],roots['r'+str(i+1)]['split'])
        for split in bundle.R:
            weights=[Fraction(r['root_weight']['numerator'],r['root_weight']['denominator'])
                     for r in roots.values() if r['split']==split]
            self.assertEqual(sum(weights),1)
            for r in roots.values():
                if r['split']==split:
                    self.assertEqual(Fraction(r['episode_weight']['numerator'],r['episode_weight']['denominator'])*bundle.R[split],
                        Fraction(r['root_weight']['numerator'],r['root_weight']['denominator']))

    def test_keep_primary_duplicates_and_input_disjoint_separate(self):
        public=[{'input':'x\n','output':'1 2\n','testtype':'stdin'}]
        private=[{'input':'x\n','output':'1\t2','testtype':'stdin'},
                 {'input':'x\n','output':'1 2','testtype':'stdin'},
                 {'input':'y\n','output':'3','testtype':'stdin'}]
        meta,ledger=bundle.case_metadata(private,public,bundle.ASCII_TOKENS)
        self.assertEqual(meta['case_count'],3)
        self.assertEqual(meta['private_input_disjoint_ordinals'],[2])
        self.assertEqual(meta['public_input_overlap_cases'],2)
        self.assertEqual(meta['raw_overlapping_expected_set_differences'],1)
        self.assertEqual(meta['canonical_overlapping_expected_set_differences'],0)
        self.assertEqual(len(ledger),3)

    def test_canonical_conflict_is_retained_flag(self):
        private=[{'input':'same','output':'1','testtype':'stdin'},
                 {'input':'same','output':'2','testtype':'stdin'}]
        meta,ledger=bundle.case_metadata(private,[],bundle.ASCII_TOKENS)
        self.assertEqual(meta['private_inputs_with_canonical_expected_conflicts'],1)
        self.assertEqual(meta['case_count'],2)

    def test_cached_missing_read_has_no_network_fallback(self):
        raw=bundle.LocalRangeFile.__new__(bundle.LocalRangeFile)
        io.RawIOBase.__init__(raw)
        raw.cache=[]
        raw.max_request=8*1024**2
        with self.assertRaisesRegex(bundle.BundleError,'no-network'):
            raw._interval(0,4)
        with self.assertRaisesRegex(bundle.BundleError,'no-network'):
            raw._fetch(0,3)

    def test_sealed_adapter_rejects_nonignored_paths(self):
        with tempfile.TemporaryDirectory() as path:
            with self.assertRaisesRegex(bundle.BundleError,'ignored-bundle-only'):
                bundle.load_root_cases(Path(path),'r','private')

    def test_utf8_input_limit_is_bytes(self):
        previous=bundle.MAX_CASE_BYTES
        try:
            bundle.MAX_CASE_BYTES=3
            with self.assertRaisesRegex(bundle.BundleError,'case-byte-cap'):
                bundle.normalize('éé',bundle.ASCII_TOKENS)
        finally: bundle.MAX_CASE_BYTES=previous


if __name__=='__main__': unittest.main()
