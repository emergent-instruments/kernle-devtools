# kernle-devtools

Admin dashboard and diagnostic tools for [kernle](https://github.com/emergent-instruments/kernle) memory stacks.

## Install

```bash
pip install kernle-devtools
```

## Usage

### Dashboard (via plugin)

```bash
kernle dev dashboard --stack my-agent
```

### Dashboard (standalone)

```bash
kernle-dev --stack my-agent dashboard
```

### Diagnostic Sessions

```bash
kernle doctor session start --stack my-agent
kernle doctor session list --stack my-agent
kernle doctor report latest --stack my-agent
```

Or standalone:

```bash
kernle-dev --stack my-agent session start
kernle-dev --stack my-agent report latest
```
