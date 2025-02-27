import json
import re
from typing import Dict, List


class ResponseAnalyzer:
    def __init__(
        self,
        files: List[str],
    ) -> None:
        self._files = files

    def read_saved_responses(self) -> List[str]:
        """
        Reads responses from the specified files and produces the total number of passages.

        Returns:
            Tuple[List[str], List[int]]: A tuple object containing a list of responses and a list of corresponding numbers of passages.
        """
        num_passages = []
        responses = []
        for filename in self._files:
            with open(filename) as f:
                ranking_exec_summaries = json.load(f)
            for summary in ranking_exec_summaries:
                for exec_info in summary["ranking_exec_summary"]:
                    responses.append(exec_info["response"])
                    num_passage = self._get_num_passages(exec_info["prompt"])
                    num_passages.append(int(num_passage))
        return responses, num_passages

    def _validate_format(self, response: str) -> bool:
        for c in response:
            if not c.isdigit() and c != "[" and c != "]" and c != ">" and c != " ":
                return False
        return True

    def _get_num_passages(self, prompt) -> int:
        search_text = ""
        if type(prompt) == str:
            search_text = prompt
        # For GPT runs, the prompt is an array of json objects with "role" and "content" as keys.
        elif type(prompt) == list:
            for message in prompt:
                search_text += message["content"]
        else:
            raise ValueError(f"Unsupported prompt format.")
        regex = r"(I will provide you with) (\d+) (passages)"
        match = re.search(regex, search_text)
        if not match:
            raise ValueError(f"Unsupported prompt format.")
        return int(match.group(2))

    def count_errors(
        self, responses: List[str], num_passages: List[int], verbose: bool = False
    ) -> Dict[str, int]:
        """
        Counts an array of different types of errors in the given responses.

        Args:
            responses (List[str]): A list of response strings.
            num_passages (List[int]): A list of the expected number of passages in each response.
            verbose (bool, optional): If True, prints the erroneous responses. Defaults to False.

        Returns:
            Dict[str, int]: A dictionary object containing counts of different types of errors.
        """
        stats_dict = {
            "ok": 0,
            "wrong_format": 0,
            "repetition": 0,
            "missing_documents": 0,
        }
        for resp, num_passage in zip(responses, num_passages):
            if not self._validate_format(resp):
                if verbose:
                    print(resp)
                stats_dict["wrong_format"] += 1
                continue
            begin, end = 0, 0
            while not resp[begin].isdigit():
                begin += 1
            while not resp[len(resp) - end - 1].isdigit():
                end += 1
            resp = resp[begin : len(resp) - end]
            ranks = resp.split("] > [")
            try:
                ranks = [int(rank) for rank in ranks]
            except ValueError:
                if verbose:
                    print(resp)
                stats_dict["wrong_format"] += 1
                continue
            if len(ranks) < num_passage:
                stats_dict["missing_documents"] += 1
                continue
            if len(ranks) > num_passage or len(set(ranks)) < num_passage:
                stats_dict["repetition"] += 1
                continue
            stats_dict["ok"] += 1
        # Create normalized dicts
        normalized_stats_dict = {}
        for key in stats_dict:
            normalized_stats_dict[key] = (stats_dict[key] / len(responses)) * 100.0
            # Round to two decimal places
            normalized_stats_dict[key] = round(normalized_stats_dict[key], 2)
        return normalized_stats_dict
