from forgeai.core.config import get_settings
from forgeai.execution.sandbox.e2b_provider import E2BSandboxProvider
from forgeai.application.repository_clone_service import RepositoryCloneService

REPOSITORY_URL = "https://github.com/octocat/Hello-World"

settings = get_settings()
sandbox_provider = E2BSandboxProvider(settings)
clone_service = RepositoryCloneService(sandbox_provider)

session = None

try:
    print("Creating E2B sandbox...")

    session = sandbox_provider.create(
        timeout_seconds=settings.e2b_sandbox_timeout
    )

    print(f"Sandbox created: {session.sandbox_id}")
    print("Cloning public GitHub repository...")

    result = clone_service.clone(
        session=session,
        repository_url=REPOSITORY_URL,
    )

    print("\nRepository clone result")
    print("-----------------------")
    print(f"Repository name : {result.repository_name}")
    print(f"Repository path : {result.repository_path}")
    print(f"Commit SHA      : {result.commit_sha}")
    print(f"Remote URL      : {result.remote_url}")

    files = sandbox_provider.list_files(
        session=session,
        directory_path="repository",
    )

    print("\nRepository files:")
    for filename in files[:20]:
        print(f"  - {filename}")

    if not result.commit_sha or len(result.commit_sha) != 40:
        raise RuntimeError("Commit SHA verification failed.")

    if not files:
        raise RuntimeError("Repository directory is empty.")

    print("\nSUCCESS: Repository cloned and verified.")
    print(f"Keep this Sandbox ID: {session.sandbox_id}")
    print("The sandbox has been left running for the next test.")

except Exception:
    if session is not None:
        try:
            sandbox_provider.terminate(session)
            print("Sandbox terminated after failed test.")
        except Exception as cleanup_error:
            print(f"Sandbox cleanup failed: {cleanup_error}")
    raise
