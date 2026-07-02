# Git Backup Info

## Remote
- URL: `https://github.com/QOULMPEFA/20260601_HKU_SummerSchool`
- PAT: (stored locally, expires Sep 8 2026)

## Backup Flow
1. PC: commit changes → `git push origin master`
2. PC: `git tag -a vX.Y -m "vX.Y — <summary>" && git push --tags`

## Version Tags
- 格式: `v<主>.<次>`，如 v1.0, v1.1, v1.2 ...
- 每次备份必须递增版本号并打 tag
- Tag 信息简要描述本次变更

## Quick Backup Commands
```bash
cd "d:\12_Projects\20260601_港大夏校\一生一芯"
git add .
git commit -m "<description>"
git push origin master
git tag -a vX.Y -m "vX.Y — <summary>"
git push --tags
```

## Current Version
- v1.0 — Initial: sCPU F6 circuit generator, 7-block subcircuit architecture, checker tools
