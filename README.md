# Herqles Code Deployer

The Code Deployer creates frameworks and workers for code deployments. 

## Stage

The CD Stage framework and worker allows the building of artifacts.

## Deploy

The CD Deploy framework and worker takes artifacts and deploys them.

## Rollback

The CD Rollback framework and worker rollback broken stages that are deployed.

## Requirements

* Herqles Framework - on framework servers
* Herqles Worker - on worker servers
* Herqles CLI - for cli access
* Python 2.7 - Not tested with newer python versions

## Quick Start Guide

### Installation

```
pip install hq-code-deployer
```

### Configuration

**See Framework and Worker configuration for a complete guide**

#### CD Stage

```
/etc/herqles/hq-framework/config.d/cdstage.yaml
```
```yaml
module: 'hqcodedeployer.framework.stage'
datacenter: 'aws-us-east'
app_type_path: '/etc/herqles/hq-framework/app_types'
build_path: '/build/herqles'
```

```
/etc/herqles/hq-worker/confid.d/cdstage.yaml
```
```yaml
module: 'hqcodedeployer.worker.stage'
datacenter: 'aws-us-east'
```

#### CD Deploy

```
/etc/herqles/hq-framework/config.d/cddeploy.yaml
```
```yaml
module: 'hqcodedeployer.framework.deploy'
datacenter: 'aws-us-east'
app_type_path: '/etc/herqles/hq-framework/app_types'
deploy_path: '/pub'
```

```
/etc/herqles/hq-worker/confid.d/cddeploy.yaml
```
```yaml
module: 'hqcodedeployer.worker.deploy'
datacenter: 'aws-us-east'
environment: 'testing'
apps:
  - app1
  - app2
  - app3
```

#### CD Rollback

```
/etc/herqles/hq-framework/config.d/cdrollback.yaml
```
```yaml
module: 'hqcodedeployer.framework.rollback'
datacenter: 'aws-us-east'
app_type_path: '/etc/herqles/hq-framework/app_types'
deploy_path: '/pub'
```

```
/etc/herqles/hq-worker/confid.d/cdrollback.yaml
```
```yaml
module: 'hqcodedeployer.worker.rollback'
datacenter: 'aws-us-east'
environment: 'testing'
apps:
  - app1
  - app2
  - app3
```

## CLI Plugin Configuration

### CD Stage

#### File

```
~/.herq/plugins/cdstage.yaml
```

#### Contents

```yaml
module: hqcodedeployer.framework.cli.stage
```

### CD Deploy

#### File

```
~/.herq/plugins/cddeploy.yaml
```

#### Contents

```yaml
module: hqcodedeployer.framework.cli.deploy
```


### CD Rollback

#### File

```
~/.herq/plugins/cdrollback.yaml
```

#### Contents

```yaml
module: hqcodedeployer.framework.cli.rollback
```
