# Lab repository scope and hygiene policy

## Scope

Paper-replication repositories contain only material directly necessary to
understand, reproduce, audit, or interpret the replication. Appropriate
material includes relevant code, configuration, environments, data
instructions, results, and methodological documentation.

## Excluded content

Repositories must not contain:

- personal services, plans, projects, or preferences;
- unrelated infrastructure, service names, or operational details;
- credentials, secrets, tokens, keys, or sensitive configuration;
- private filesystem paths, identities, contact information, hostnames, or
  other personal data;
- planned, prospective, or otherwise unobserved hardware presented as part of
  a completed run;
- logs, artifacts, datasets, or binaries that are unnecessary, restricted, or
  privacy-sensitive.

Use neutral lab terminology and portable paths, identifiers, and examples.

## Experimental resource controls

Until measured capacity supports a validated change, permit only one
experimental GPU workload per host at a time.

Every experimental job must:

- use an explicitly assigned GPU UUID;
- set `MemoryHigh`, `MemoryMax`, and `CPUQuota`;
- set defined CPU nice and I/O priority values;
- refuse startup when available memory is below the recorded minimum
  threshold;
- run in isolation from unrelated and non-experimental services;
- terminate under resource pressure without destabilizing the host or
  unrelated workloads.

Experimental tooling must never stop, signal, reconfigure, or place unrelated
services in an experimental cgroup.

Before changing concurrency limits, recapture and validate the host's actual
hardware and memory capacity. Completed run manifests record observed hardware
and runtime conditions only; they never substitute planned or prospective
hardware.

## Run records

Each completed run record should identify:

- the code and configuration revision;
- the observed hardware and software environment;
- applied resource limits and scheduling priorities;
- the recorded startup memory threshold and observed available memory;
- inputs, outputs, status, and relevant failure conditions;
- any deviations required to interpret or reproduce the result.

## Pre-publication hygiene checklist

- [ ] Every tracked file is necessary to understand, reproduce, audit, or
      interpret the replication.
- [ ] Personal services, plans, and unrelated operational details are absent.
- [ ] Unrelated infrastructure and service names are absent or generalized.
- [ ] Credentials, secrets, tokens, keys, and sensitive configuration are
      absent.
- [ ] Private paths, identities, contact data, hostnames, and personal metadata
      are absent.
- [ ] Examples and configuration use neutral lab terminology and portable
      placeholders.
- [ ] Run manifests contain only observed hardware and runtime conditions.
- [ ] Prospective or unobserved hardware is not represented as completed-run
      hardware.
- [ ] Resource limits, startup thresholds, isolation, and
      pressure-termination behavior are documented.
- [ ] Logs and artifacts have been reviewed for sensitive or irrelevant
      content.
- [ ] Repository history and generated files have been checked for excluded
      content.
- [ ] Reproduction instructions work from a clean environment without private
      dependencies.
