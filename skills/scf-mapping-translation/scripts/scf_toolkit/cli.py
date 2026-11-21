"""Portable command line entry point; no credentials or cloud service required."""
import argparse
import json
from pathlib import Path
import sys
from . import __version__
from .common import DataError, digest, load, write_json
from .catalog import extract
from .ledger import validate
from .retrieval import Search
from .terms import Terminology, import_glossaries
from .translation import check_units
from .workbook import build_workbook, verify_workbook


def main(argv=None):
    parser = argparse.ArgumentParser(prog='scf-toolkit')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('import-scf', help='Import a local, explicitly versioned SCF workbook including AOs')
    p.add_argument('--xlsx', type=Path, required=True)
    p.add_argument('--scf-version', required=True)
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('import-glossaries', help='Freeze private source files and filter eligible supplementary entries')
    for name in ('afta', 'supplementary', 'markdown', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p = sub.add_parser('lookup', help='AFTA-first whole-heading terminology candidates')
    p.add_argument('--references', type=Path, required=True)
    p.add_argument('terms', nargs='*')
    p.add_argument('--text')
    p = sub.add_parser('shortlist', help='Unicode BM25 discovery using control descriptions and AOs')
    p.add_argument('--catalog', type=Path, required=True)
    p.add_argument('--query', required=True)
    p.add_argument('--k', type=int, default=15)
    p.add_argument('--out', type=Path)
    for command in ('validate', 'build-xlsx', 'check-xlsx'):
        p = sub.add_parser(command)
        for name in ('ledger', 'catalog', 'inventory'):
            p.add_argument('--' + name, type=Path, required=True)
        if command == 'validate':
            p.add_argument('--report', type=Path)
        elif command == 'build-xlsx':
            p.add_argument('--out', type=Path, required=True)
            p.add_argument('--template', type=Path)
        else:
            p.add_argument('--xlsx', type=Path, required=True)
    p = sub.add_parser('translation-qa')
    p.add_argument('jsonl', type=Path)
    p.add_argument('--references', type=Path)
    p.add_argument('--report', type=Path)
    args = parser.parse_args(argv)
    exit_code = 0
    try:
        if args.command == 'import-scf':
            catalog = extract(args.xlsx, args.scf_version, args.out)
            result = {'status': 'CATALOG_IMPORTED', 'scf_version': catalog['scf_version'], **catalog['counts'],
                      'sha256': digest(args.out)}
        elif args.command == 'import-glossaries':
            result = import_glossaries(args.afta, args.supplementary, args.markdown, args.out)
        elif args.command == 'lookup':
            if not args.terms and args.text is None:
                parser.error('lookup requires terms or --text')
            terms = Terminology(args.references)
            result = terms.scan(args.text) if args.text is not None else [terms.lookup(t) for t in args.terms]
        elif args.command == 'shortlist':
            result = {'query': args.query, 'decision': 'CANDIDATE_ONLY',
                      'candidates': Search(load(args.catalog)).shortlist(args.query, args.k)}
            if args.out:
                write_json(args.out, result)
        elif args.command in ('validate', 'build-xlsx', 'check-xlsx'):
            doc, catalog, inventory = load(args.ledger), load(args.catalog), load(args.inventory)
            result, rows = validate(doc, catalog, inventory, digest(args.catalog), digest(args.inventory))
            if result['status'] != 'READY_FOR_EXPORT':
                exit_code = 1
            elif args.command == 'build-xlsx':
                result = build_workbook(doc, catalog, inventory, args.out, digest(args.catalog), digest(args.inventory), args.template)
            elif args.command == 'check-xlsx':
                result = verify_workbook(args.xlsx, rows)
            if args.command == 'validate' and args.report:
                write_json(args.report, result)
        else:
            result = check_units(args.jsonl, Terminology(args.references) if args.references else None)
            exit_code = 0 if result['status'] == 'READY_FOR_SEMANTIC_REVIEW' else 1
            if args.report:
                write_json(args.report, result)
    except Exception as error:
        # Keep the command interface machine-readable even for a corrupt workbook/library error.
        # KeyboardInterrupt/SystemExit remain interruptible (they do not subclass Exception).
        result = {'status': 'NOT_FINAL', 'error': str(error)}
        exit_code = 1
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
