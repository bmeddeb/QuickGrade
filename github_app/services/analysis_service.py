"""
Code analysis service using Lizard and Complexipy.
"""

import logging
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
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
            # Analyze entire directory
            analysis = lizard.analyze(
                paths=[self.repo_path],
                threads=4,
                exts=lizard.get_extensions([]),  # Use default extensions
            )

            for file_info in analysis:
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
            # Find all Python files
            python_files = []
            for root, _, files in os.walk(self.repo_path):
                for file in files:
                    if file.endswith(".py"):
                        python_files.append(os.path.join(root, file))

            if not python_files:
                return results

            # Run complexipy on the directory
            # complexipy outputs JSON with -j flag
            cmd = ["complexipy", self.repo_path, "-j"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

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
        Run all analyses in parallel threads.
        Returns combined results.
        """
        with ThreadPoolExecutor(max_workers=2) as executor:
            lizard_future = executor.submit(self.analyze_with_lizard)
            complexipy_future = executor.submit(self.analyze_python_with_complexipy)

            lizard_results = lizard_future.result()
            complexipy_results = complexipy_future.result()

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
