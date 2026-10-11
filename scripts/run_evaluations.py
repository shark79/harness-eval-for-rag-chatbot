#!/usr/bin/env python3
"""Run the independent Harness Evals suite without uploading the CSV to the knowledge base."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',choices=('baseline','chatbot'),default='baseline')
    parser.add_argument('--limit',type=int,default=26)
    parser.add_argument('--mode',choices=('offline','decisions'),default=None)
    args=parser.parse_args()
    from agents.evals.evaluation_service import EvaluationService
    # CLI uses the same central local environment loader as the server.
    from backend.app.config.settings import Settings
    settings=Settings.load(ROOT)
    report=EvaluationService(ROOT,mode=args.mode or settings.eval_mode,api_key=settings.openai_api_key).run(source=args.source,limit=args.limit)
    print(json.dumps({'run_id':report['run_id'],'summary':report['summary'],'artifacts':report['artifacts']},indent=2))


if __name__=='__main__': main()
