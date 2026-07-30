# Paper-stated environment

The paper repository recommends:

- Python 3.10;
- PyTorch 2.5.1 with CUDA 12.1;
- Transformers 4.45.2;
- TRL 0.9.6;
- PEFT 0.18.1.

It does not publish a complete lockfile. Its README setup also omits `rich`,
although TRL 0.9.6 imports it and the repository's broad `requirements.txt`
lists it. The repository's editable package does not install that logging
extra.

`requirements.lock.txt` records the complete environment resolved on
2026-07-30 after following the stated core pins and installing the dependencies
needed by all four released CLIs. It is a reconstruction of the documented
environment, not evidence of the authors' exact transitive package versions.

Create it with:

```bash
bash environments/paper/create.sh
```

The script refuses to overwrite an existing environment. It performs import,
CLI, and CUDA smoke tests after installation.

PyTorch 2.5.1+cu121 successfully executes CUDA kernels on the workstation RTX
4090. It is not expected to support the Blackwell RTX PRO 6000; that host uses a
separately declared compatibility environment.
