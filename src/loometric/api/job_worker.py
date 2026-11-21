"""Private outer job process; native imports occur only inside its memory guard."""

from loometric.api.worker import serve

if __name__ == "__main__":
    raise SystemExit(serve(job_mode=True))
