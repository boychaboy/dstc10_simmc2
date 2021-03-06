"""Script evaluates response retrieval using GT responses.

Expected format.

[
    "dialog_id": <dialog_id>,
    "candidates_scores": [
        {
            "turn_id": <turn_id>,
            "scores": [
                <list of 100 floats>
            ]
        }
        ...
    ]
    ...
]

Author(s): Satwik Kottur
"""


import argparse
import json

import numpy as np


def evaluate_response_retrieval(gt_responses, model_scores, single_round_eval=False):
    """Evaluates response retrieval using the raw data and model predictions.

    Args:
        gt_responses: Ground truth responses.
        model_scores: Scores assigned by the model to the candidates.
        single_round_eval: Evaluate only for the last turn.

    If in single round evaluation model (mostly for hidden test-std split),
    use hidden gt_index field. Else, 0th element is the ground truth for other
    splits.
    """
    gt_index_pool = {
        ii["dialogue_idx"]: ii for ii in gt_responses["retrieval_candidates"]
    }
    gt_ranks = []
    for model_datum in model_scores:
        dialog_id = model_datum["dialog_id"]
        gt_datum = gt_index_pool[dialog_id]["retrieval_candidates"]
        num_gt_rounds = len(gt_datum)
        for round_id, round_datum in enumerate(model_datum["candidate_scores"]):
            round_id = round_datum["turn_id"]
            # Skip if single_round_eval and this is not the last round.
            if single_round_eval and round_id != num_gt_rounds - 1:
                continue

            gt_index = gt_datum[round_id]["gt_index"]
            current_turn = round_datum["turn_id"]
            round_scores = round_datum["scores"]
            gt_score = round_scores[gt_index]
            gt_ranks.append(np.sum(np.array(round_scores) > gt_score) + 1)
    gt_ranks = np.array(gt_ranks)
    print("#Instances evaluated retrieval: {}".format(gt_ranks.size))

    return {
        "r1": np.mean(gt_ranks <= 1),
        "r1_std_err": np.std(gt_ranks <= 1) / np.sqrt(gt_ranks.size),
        "r5": np.mean(gt_ranks <= 5),
        "r5_std_err": np.std(gt_ranks <= 5) / np.sqrt(gt_ranks.size),
        "r10": np.mean(gt_ranks <= 10),
        "r10_std_err": np.std(gt_ranks <= 10) / np.sqrt(gt_ranks.size),
        "mean": np.mean(gt_ranks),
        "mean_std_err": np.std(gt_ranks) / np.sqrt(gt_ranks.size),
        "mrr": np.mean(1 / gt_ranks),
        "mrr_std_err": np.std(1 / gt_ranks) / np.sqrt(gt_ranks.size),
    }


def main(args):
    print("Reading: {}".format(args["retrieval_json_path"]))
    with open(args["retrieval_json_path"], "r") as file_id:
        gt_responses = json.load(file_id)
    print("Reading: {}".format(args["model_score_path"]))
    with open(args["model_score_path"], "r") as file_id:
        model_scores = json.load(file_id)
    retrieval_metrics = evaluate_response_retrieval(
        gt_responses, model_scores, args["single_round_evaluation"]
    )
    print(retrieval_metrics)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Response Retrieval Evaluation")
    parser.add_argument(
        "--retrieval_json_path",
        default="data/furniture_train_retrieval_candidates.json",
        help="Data with retrieval candidates, gt",
    )
    parser.add_argument(
        "--model_score_path",
        default=None,
        help="Candidate scores generated by the model",
    )
    parser.add_argument(
        "--single_round_evaluation",
        dest="single_round_evaluation",
        action="store_true",
        default=False,
        help="Single round evaluation for hidden split",
    )
    try:
        parsed_args = vars(parser.parse_args())
    except (IOError) as msg:
        parser.error(str(msg))
    main(parsed_args)
