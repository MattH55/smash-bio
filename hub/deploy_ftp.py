"""Deploy website/ to smash-bio.org over explicit FTPS (port 21).

Usage (password is prompted, never stored):
    python deploy_ftp.py --list            # show what is on the server, change nothing
    python deploy_ftp.py --dry-run         # show what would be uploaded
    python deploy_ftp.py                   # upload new/changed files
    python deploy_ftp.py --backup          # first download the current remote site to ../remote_backup_<date>/

Only uploads; never deletes remote files. Files whose remote size already matches are skipped.
"""
import argparse
import datetime
import ftplib
import getpass
import hashlib
import json
import os
from pathlib import Path

HOST = "ftp.smash-bio.org"
USER = os.environ.get("SMASH_FTP_USER", "SMASHBIO@smash-bio.org")
REMOTE_ROOT = "/home/smasrjbl/public_html"
LOCAL_ROOT = Path(__file__).resolve().parent.parent / "website"
MANIFEST = Path(__file__).resolve().parent / "deploy_manifest.json"  # md5 of what was last uploaded per file


class ReusedSessionFTP_TLS(ftplib.FTP_TLS):
    """Many hosts (Pure-FTPd/vsftpd with ssl reuse) require the data channel to reuse the control TLS session."""
    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session)
        return conn, size


def connect():
    pw = os.environ.get("SMASH_FTP_PASSWORD") or getpass.getpass(f"FTP password for {USER}: ")
    ftp = ReusedSessionFTP_TLS(timeout=120)
    ftp.connect(HOST, 21)
    ftp.login(USER, pw)
    ftp.prot_p()  # encrypt the data channel too
    return ftp


def resolve_root(ftp):
    """FTP accounts are often chrooted: the account home may already be the web root."""
    for cand in (REMOTE_ROOT, "/smash-bio.org", "/public_html", "."):
        try:
            ftp.cwd(cand)
            return ftp.pwd()
        except ftplib.error_perm:
            continue
    raise SystemExit("Could not find the web root on the server")


def remote_sizes(ftp, root):
    sizes = {}

    def walk(d):
        try:
            entries = list(ftp.mlsd(d, facts=["type", "size"]))
        except ftplib.error_perm:
            return
        for name, f in entries:
            if name in (".", ".."):
                continue
            p = f"{d}/{name}"
            if f.get("type") == "dir":
                walk(p)
            elif f.get("type") == "file":
                sizes[p[len(root) + 1:]] = int(f.get("size", -1))
    walk(root)
    return sizes


def ensure_dir(ftp, root, rel_dir, made):
    parts = [p for p in rel_dir.split("/") if p]
    cur = root
    for p in parts:
        cur = f"{cur}/{p}"
        if cur in made:
            continue
        try:
            ftp.mkd(cur)
        except ftplib.error_perm:
            pass  # exists
        made.add(cur)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backup", action="store_true")
    a = ap.parse_args()

    ftp = connect()
    root = resolve_root(ftp)
    print("remote web root:", root)
    rs = remote_sizes(ftp, root)
    print(f"{len(rs)} files currently on the server")
    if a.list:
        for k in sorted(rs)[:300]:
            print(f"  {rs[k]:>10}  {k}")
        ftp.quit()
        return
    if a.backup:
        dest = LOCAL_ROOT.parent / f"remote_backup_{datetime.date.today().isoformat()}"
        for k in rs:
            out = dest / k
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "wb") as f:
                ftp.retrbinary(f"RETR {root}/{k}", f.write)
        print("backed up remote site to", dest)

    local = [p for p in LOCAL_ROOT.rglob("*") if p.is_file()]
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    todo, hashes, unreadable = [], {}, []
    for p in local:
        rel = p.relative_to(LOCAL_ROOT).as_posix()
        try:
            h = hashlib.md5(p.read_bytes()).hexdigest()
        except OSError as e:
            # e.g. an OneDrive "online-only" placeholder that cannot be downloaded right now.
            # Never abort the deploy and never touch the remote copy: just report it.
            same_size = rs.get(rel) == p.stat().st_size
            unreadable.append((rel, e.errno, same_size))
            continue
        hashes[rel] = h
        # upload when content changed since the last deploy (sizes alone miss same-length edits) or remote is missing/different
        if manifest.get(rel) != h or rs.get(rel) != p.stat().st_size:
            todo.append((p, rel))
    overwrite = [rel for _, rel in todo if rel in rs]
    if unreadable:
        print(f"\n!! {len(unreadable)} local file(s) could not be read and were SKIPPED (remote copies left as they are):")
        for rel, errno, same_size in unreadable:
            print(f"   {rel}  (errno {errno}; local size {'matches' if same_size else 'DIFFERS from or is missing on'} the live copy)")
        print("   Likely OneDrive online-only files: right-click the folder > 'Always keep on this device', wait for sync, re-run.\n")
    print(f"{len(todo)} files to upload ({len(overwrite)} replace existing remote files)")
    for rel in overwrite[:40]:
        print("  replaces:", rel)
    if a.dry_run:
        ftp.quit()
        return
    made = set()
    for i, (p, rel) in enumerate(todo, 1):
        ensure_dir(ftp, root, rel.rsplit("/", 1)[0] if "/" in rel else "", made)
        with open(p, "rb") as f:
            ftp.storbinary(f"STOR {root}/{rel}", f)
        manifest[rel] = hashes[rel]
        if i % 25 == 0 or i == len(todo):
            print(f"  uploaded {i}/{len(todo)}")
            MANIFEST.write_text(json.dumps(manifest, indent=0, sort_keys=True))
    MANIFEST.write_text(json.dumps(manifest, indent=0, sort_keys=True))
    ftp.quit()
    print("done: https://smash-bio.org/")


if __name__ == "__main__":
    main()
