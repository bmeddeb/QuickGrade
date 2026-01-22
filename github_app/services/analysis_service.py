"""
Code analysis service using Lizard and Complexipy.
"""

import logging
import os
import subprocess
from typing import TYPE_CHECKING

import lizard

if TYPE_CHECKING:
    from github_app.models import Repository

logger = logging.getLogger(__name__)

# File extensions supported by Lizard
LIZARD_EXTENSIONS = {
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh",
    ".java", ".cs", ".js", ".ts", ".jsx", ".tsx",
    ".py", ".rb", ".go", ".swift", ".m", ".mm",
    ".php", ".scala", ".lua", ".rs", ".kt", ".kts",
}

# Directories to exclude from analysis
EXCLUDE_DIRS = {
    "node_modules", ".git", "vendor", "venv", ".venv", "env",
    "__pycache__", ".tox", ".pytest_cache", ".mypy_cache",
    "dist", "build", ".next", ".nuxt", "coverage",
    "target", "out", "bin", "obj", ".gradle",
}


class AnalysisService:
    """Code complexity analysis using Lizard and Complexipy."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def _should_analyze_file(self, file_path: str) -> bool:
        """Check if file should be analyzed based on extension."""
        _, ext = os.path.splitext(file_path)
        return ext.lower() in LIZARD_EXTENSIONS

    def _get_language(self, file_path: str) -> str:
        """Get language name from file extension."""
        ext_to_lang = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript",
            ".tsx": "TypeScript",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
            ".cc": "C++",
            ".cxx": "C++",
            ".h": "C/C++",
            ".hpp": "C++",
            ".cs": "C#",
            ".go": "Go",
            ".rb": "Ruby",
            ".swift": "Swift",
            ".rs": "Rust",
            ".kt": "Kotlin",
            ".kts": "Kotlin",
            ".php": "PHP",
            ".scala": "Scala",
            ".lua": "Lua",
            ".m": "Objective-C",
            ".mm": "Objective-C++",
        }
        _, ext = os.path.splitext(file_path)
        return ext_to_lang.get(ext.lower(), "Unknown")

    def analyze_with_lizard(self) -> list[dict]:
        """
        Analyze repository with Lizard for cyclomatic complexity.
        Returns list of file analysis results.
        """
        results = []

        try:
            logger.info(f"Starting Lizard analysis for {self.repo_path}")

            # Build exclude pattern for common non-source directories
            exclude_patterns = [f"*/{d}/*" for d in EXCLUDE_DIRS]

            # Analyze entire directory
            # Use threads=1 to avoid multiprocessing issues in Celery workers
            analysis = lizard.analyze(
                paths=[self.repo_path],
                threads=1,
                exts=lizard.get_extensions([]),  # Use default extensions
                exclude_pattern=exclude_patterns,
            )

            logger.info(f"Lizard analysis generator created, iterating over files...")

            file_count = 0
            for file_info in analysis:
                file_count += 1
                if file_count % 50 == 0:
                    logger.info(f"Lizard: processed {file_count} files so far...")

                # Skip files outside repo (shouldn't happen, but safety check)
                if not file_info.filename.startswith(self.repo_path):
                    continue

                # Get relative path
                rel_path = os.path.relpath(file_info.filename, self.repo_path)

                file_result = {
                    "file_path": rel_path,
                    "language": self._get_language(file_info.filename),
                    "nloc": file_info.nloc,
                    "ccn": file_info.CCN,
                    "token_count": file_info.token_count,
                    "function_count": len(file_info.function_list),
                    "functions": [],
                }

                # Extract function-level metrics
                for func in file_info.function_list:
                    file_result["functions"].append({
                        "function_name": func.name,
                        "long_name": func.long_name,
                        "start_line": func.start_line,
                        "end_line": func.end_line,
                        "nloc": func.nloc,
                        "ccn": func.cyclomatic_complexity,
                        "token_count": func.token_count,
                        "parameter_count": len(func.parameters),
                    })

                results.append(file_result)

            logger.info(f"Lizard analysis complete: {len(results)} files analyzed")

        except Exception as e:
            logger.exception(f"Lizard analysis failed: {e}")

        return results

    def analyze_python_with_complexipy(self) -> dict[str, int]:
        """
        Analyze Python files with Complexipy for cognitive complexity.
        Returns dict mapping file paths to cognitive complexity scores.
        """
        results = {}

        try:
            # Find all Python files, excluding common non-source directories
            python_files = []
            for root, dirs, files in os.walk(self.repo_path):
                # Modify dirs in-place to skip excluded directories
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

                for file in files:
                    if file.endswith(".py"):
                        python_files.append(os.path.join(root, file))

            if not python_files:
                logger.info("No Python files found, skipping complexipy analysis")
                return results

            logger.info(f"Starting complexipy analysis for {len(python_files)} Python files...")

            # Run complexipy on the directory
            # complexipy outputs JSON with -j flag
            # Use -x to exclude common directories
            exclude_args = []
            for d in EXCLUDE_DIRS:
                exclude_args.extend(["-x", d])

            cmd = ["complexipy", self.repo_path, "-j"] + exclude_args
            logger.info(f"Running complexipy command: {' '.join(cmd[:5])}...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
            )
            logger.info(f"Complexipy finished with return code {result.returncode}")

            if result.stderr:
                logger.warning(f"Complexipy stderr: {result.stderr[:500]}")

            if result.returncode == 0 and result.stdout:
                import json

                try:
                    data = json.loads(result.stdout)
                    # Complexipy output format varies; handle accordingly
                    if isinstance(data, list):
                        for item in data:
                            file_path = item.get("file", item.get("path", ""))
                            if file_path:
                                rel_path = os.path.relpath(file_path, self.repo_path)
                                complexity = item.get("complexity", item.get("cognitive_complexity", 0))
                                results[rel_path] = complexity
                    elif isinstance(data, dict):
                        for file_path, complexity in data.items():
                            rel_path = os.path.relpath(file_path, self.repo_path)
                            if isinstance(complexity, dict):
                                results[rel_path] = complexity.get("complexity", 0)
                            else:
                                results[rel_path] = complexity

                except json.JSONDecodeError:
                    logger.warning("Failed to parse complexipy JSON output")

            logger.info(f"Complexipy analysis complete: {len(results)} files analyzed")

        except subprocess.TimeoutExpired:
            logger.warning("Complexipy analysis timed out")
        except FileNotFoundError:
            logger.warning("Complexipy not found in PATH")
        except Exception as e:
            logger.exception(f"Complexipy analysis failed: {e}")

        return results

    def analyze_all(self) -> dict:
        """
        Run all analyses sequentially.
        Returns combined results.
        """
        logger.info(f"Starting code analysis for {self.repo_path}")

        # Run sequentially to avoid multiprocessing issues in Celery workers
        logger.info("Phase 1: Running Lizard analysis...")
        lizard_results = self.analyze_with_lizard()
        logger.info(f"Lizard complete: {len(lizard_results)} files analyzed")

        logger.info("Phase 2: Running Complexipy analysis...")
        complexipy_results = self.analyze_python_with_complexipy()
        logger.info(f"Complexipy complete: {len(complexipy_results)} files analyzed")

        # Merge complexipy results into lizard results
        for file_result in lizard_results:
            if file_result["language"] == "Python":
                file_path = file_result["file_path"]
                if file_path in complexipy_results:
                    file_result["cognitive_complexity"] = complexipy_results[file_path]

        return {
            "files": lizard_results,
            "total_files": len(lizard_results),
            "total_functions": sum(f["function_count"] for f in lizard_results),
        }


def save_analysis_results(repository: "Repository", analysis_data: dict) -> tuple[int, int]:
    """
    Save analysis results to database.
    Returns (files_saved, functions_saved).
    """
    from github_app.models import FileAnalysis, FunctionAnalysis

    files_saved = 0
    functions_saved = 0

    for file_data in analysis_data.get("files", []):
        # Create FileAnalysis record
        file_analysis = FileAnalysis.objects.create(
            repository=repository,
            file_path=file_data["file_path"],
            language=file_data["language"],
            nloc=file_data["nloc"],
            ccn=file_data["ccn"],
            token_count=file_data["token_count"],
            function_count=file_data["function_count"],
            cognitive_complexity=file_data.get("cognitive_complexity"),
        )
        files_saved += 1

        # Create FunctionAnalysis records
        function_records = [
            FunctionAnalysis(
                file_analysis=file_analysis,
                function_name=func["function_name"],
                long_name=func["long_name"],
                start_line=func["start_line"],
                end_line=func["end_line"],
                nloc=func["nloc"],
                ccn=func["ccn"],
                token_count=func["token_count"],
                parameter_count=func["parameter_count"],
            )
            for func in file_data.get("functions", [])
        ]

        if function_records:
            FunctionAnalysis.objects.bulk_create(function_records)
            functions_saved += len(function_records)

    logger.info(f"Saved {files_saved} file analyses, {functions_saved} function analyses")
    return files_saved, functions_saved
