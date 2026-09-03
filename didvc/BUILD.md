# Building unomi-did-vc standalone (TASK-031)

This repository copy does not contain the full Apache Unomi source tree, but
the module builds standalone against published artifacts:

- the **ASF-published parent** `org.apache.unomi:unomi-root:3.1.0-SNAPSHOT`
  is checked in at the repository root as `pom.xml` (fetched from
  `repository.apache.org`; provides plugin/dependency management);
- `org.apache.unomi` snapshot dependencies (`unomi-api`, `unomi-bom`,
  `unomi-persistence-spi`, …) resolve from the **Apache snapshot
  repository**, which `didvc/pom.xml` declares explicitly;
- `didvc/pom.xml` carries the module list so the reactor orders the seven
  modules correctly.

## Requirements

- JDK 17+ (verified with OpenJDK 25)
- Maven 3.9+
- Network access to `repo.maven.apache.org` and `repository.apache.org`

## Commands

```bash
# Run the test suite (surefire)
mvn -f didvc/pom.xml test

# Build all artifacts, including the didvc-edge Spring Boot fat jar
mvn -f didvc/pom.xml -DskipTests package

# Run a single module's tests
mvn -f didvc/pom.xml -pl didvc-sd-jwt test
```

## Verified results (2026-09-03, OpenJDK 25.0.4 / Maven 3.9.12)

| Check | Result |
|---|---|
| `mvn -f didvc/pom.xml test` | **BUILD SUCCESS — 220 tests, 0 failures, 0 errors, 0 skipped** (aggregated from surefire reports; README cites 217 — current tree carries 220) |
| `mvn -f didvc/pom.xml -DskipTests package` | **BUILD SUCCESS** — 7 artifacts, incl. `didvc-edge/target/unomi-did-vc-edge-3.1.0-SNAPSHOT.jar` (executable fat jar, ~50 MB) |

Note on timestamps: archive entry dates inside the jars are pinned to the
ASF parent's reproducible-build `outputTimestamp` (2022-12-11) — the jars
themselves are freshly compiled (manifest `Build-Jdk-Spec` and class bytes
match the current build).

## Updating the root parent

The checked-in root `pom.xml` mirrors
`https://repository.apache.org/content/repositories/snapshots/org/apache/unomi/unomi-root/3.1.0-SNAPSHOT/`
(fetch the latest timestamped `unomi-root-*.pom` from `maven-metadata.xml`
to refresh it).
