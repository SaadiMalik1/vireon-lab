"""
Secure Product Development Framework (SPDF) Auditor.

FDA Section 524B requires medical device manufacturers to implement and document an SPDF.
This module audits the NeuroShield project repository for SPDF compliance artifacts,
such as Threat Models, SBOMs, Risk Management files, and static security checks.
"""

import os
import json
from typing import Dict, Any

class SPDFAuditor:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.artifacts_dir = os.path.join(project_root, "artifacts")
        
    def audit(self) -> Dict[str, Any]:
        print(f"[SPDFAuditor] Auditing project root: {self.project_root} for FDA 524B SPDF compliance...")
        
        results = {
            "sbom_present": False,
            "threat_model_present": False,
            "architecture_doc_present": False,
            "tests_present": False,
            "overall_spdf_score": 0.0,
            "gaps": []
        }
        
        # 1. Check SBOM
        sbom_path = os.path.join(self.project_root, "sbom.json")
        if os.path.exists(sbom_path):
            results["sbom_present"] = True
            results["overall_spdf_score"] += 25.0
        else:
            results["gaps"].append("Missing Machine-Readable SBOM (sbom.json) - FDA 524B Core Requirement")
            
        # 2. Check Threat Model (STRIDE)
        # We look for a threat_models dir or stride.json
        tm_path = os.path.join(self.project_root, "threat_model.json")
        if os.path.exists(tm_path):
            results["threat_model_present"] = True
            results["overall_spdf_score"] += 25.0
        else:
            results["gaps"].append("Missing Threat Model artifact (threat_model.json) - Required for SPDF")
            
        # 3. Check Architecture Documentation
        arch_path = os.path.join(self.project_root, "architecture.md")
        if os.path.exists(arch_path):
            results["architecture_doc_present"] = True
            results["overall_spdf_score"] += 25.0
        else:
            results["gaps"].append("Missing Architecture Documentation (architecture.md) - Required for Secure Design")
            
        # 4. Check Test Coverage (heuristically look for 'tests' directory)
        tests_path = os.path.join(self.project_root, "tests")
        if os.path.exists(tests_path) and os.path.isdir(tests_path):
            results["tests_present"] = True
            results["overall_spdf_score"] += 25.0
        else:
            results["gaps"].append("Missing 'tests' directory - Validation & Verification is a core SPDF pillar")
            
        return results

    def print_report(self, results: Dict[str, Any]):
        print("\n" + "="*50)
        print(" FDA 524B SPDF AUDIT REPORT")
        print("="*50)
        print(f" SBOM Present:           {'[PASS]' if results['sbom_present'] else '[FAIL]'}")
        print(f" Threat Model Present:   {'[PASS]' if results['threat_model_present'] else '[FAIL]'}")
        print(f" Architecture Doc:       {'[PASS]' if results['architecture_doc_present'] else '[FAIL]'}")
        print(f" Verification (Tests):   {'[PASS]' if results['tests_present'] else '[FAIL]'}")
        print("-" * 50)
        print(f" Overall SPDF Score:     {results['overall_spdf_score']:.1f}%")
        
        if results["gaps"]:
            print("\n Identified Gaps:")
            for gap in results["gaps"]:
                print(f"  - {gap}")
        else:
            print("\n [✓] No SPDF compliance gaps identified.")
        print("="*50 + "\n")
