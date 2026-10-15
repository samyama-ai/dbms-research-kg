# Demo

Narrated walkthrough of the DBMS Research KG on a fast, real subset.

```bash
python -m demo.demo
```
Record/regenerate:
```bash
asciinema rec --overwrite --cols 92 --rows 32 --idle-time-limit 2.0 \
  -c "bash -c 'python -m demo.demo'" demo/dbms_research.cast
agg demo/dbms_research.cast demo/dbms_research.gif
```
