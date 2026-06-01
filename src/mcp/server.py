from __future__ import annotations

from src.mcp.tools import jobs


def build_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - depends on optional runtime package
        raise RuntimeError("Install the MCP runtime first: pip install -e .") from exc

    server = FastMCP("zighang-personal")

    server.tool()(jobs.search_jobs)
    server.tool()(jobs.search_jobs_posted_on)
    server.tool()(jobs.search_pinned_jobs)
    server.tool()(jobs.search_latest_it_jobs)
    server.tool()(jobs.search_today_it_jobs)
    server.tool()(jobs.search_latest_jobs_for_me)
    server.tool()(jobs.get_job_detail)
    server.tool()(jobs.list_filter_options)
    server.tool()(jobs.recommend_jobs)
    server.tool()(jobs.explain_job_match)
    server.tool()(jobs.save_filter_profile)
    server.tool()(jobs.list_filter_profiles)
    server.tool()(jobs.update_filter_profile)
    server.tool()(jobs.delete_filter_profile)
    server.tool()(jobs.daily_job_digest)
    server.tool()(jobs.track_job_status)
    server.tool()(jobs.list_tracked_jobs)
    server.tool()(jobs.mark_job_status)
    server.tool()(jobs.list_saved_jobs)
    server.tool()(jobs.get_user_preferences)
    server.tool()(jobs.update_user_preferences)
    server.tool()(jobs.update_user_preferences_from_text)
    server.tool()(jobs.clear_user_preferences)
    server.tool()(jobs.load_resume_profile)
    server.tool()(jobs.update_resume_profile)
    server.tool()(jobs.analyze_resume_profile)
    server.tool()(jobs.extract_skills_from_resume)
    server.tool()(jobs.extract_projects_from_portfolio)

    return server


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
