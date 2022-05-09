import argparse
import json
import os
from typing import Dict

import pandas as pd
from bokeh.models import (Arrow, ColumnDataSource, NormalHead,
                          NumeralTickFormatter, Range1d, TeeHead)
from bokeh.models.tools import HoverTool
from bokeh.palettes import d3, grey
from bokeh.plotting import figure, output_file, save


def option_parser():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "-s",
        "--src_file_path",
        required=True,
        type=str,
        help="The path to source json file",
    )
    arg_parser.add_argument(
        "-d",
        "--dest_dir",
        default="./",
        type=str,
        help="The path to dest result file"
    )
    arg_parser.add_argument(
        "-y",
        "--y_axis",
        required=True,
        type=str,
        help='y_axis. ["core", "task"]'
    )
    arg_parser.add_argument(
        "-hdm",
        "--highlight_deadline_miss",
        required=False,
        action="store_true",
        help="Highlight tasks in which deadline misses occurred",
    )
    arg_parser.add_argument(
        "-l",
        "--draw_legend",
        required=False,
        action="store_true",
        help="Draw a legend for each task",
    )
    args = arg_parser.parse_args()

    return (
        args.src_file_path,
        args.dest_dir,
        args.y_axis,
        args.highlight_deadline_miss,
        args.draw_legend,
    )


class QuadStyleGetter():
    def __init__(
        self,
        source_dict: Dict,
        highlight_deadline_miss: bool,
        y_axis: str
    ) -> None:
        # Initialize variables
        self._highlight_deadline_miss = highlight_deadline_miss
        self._y_axis = y_axis
        self._all_pattern = [
            " ",
            ".",
            "o",
            "-",
            "|",
            "+",
            '"',
            ":",
            "@",
            "/",
            "\\",
            "x",
            ",",
            "`",
            "v",
            ">",
            "*",
        ]

        # get key_IDs
        if y_axis == "core":
            # get taskIDs
            taskIDs = set()
            for task in source_dict["taskSet"]:
                taskIDs.add(task["taskID"])
            key_IDs = sorted(list(taskIDs))
        elif y_axis == "task":
            # get coreIDs
            coreIDs = set()
            for task in source_dict["taskSet"]:
                coreIDs.add(task["taskID"])
            key_IDs = sorted(list(coreIDs))
        else:
            raise NotImplementedError()

        # create color dict
        self._color_dict = {}
        if highlight_deadline_miss:
            self._color_dict["deadlineMiss"] = "red"
            greys = grey(len(key_IDs) + 2)
            for key_ID in key_IDs:
                self._color_dict[str(key_ID)] = greys[key_ID + 1]
        else:
            colors = d3["Category20"][20]
            for key_ID in key_IDs:
                self._color_dict[str(key_ID)] = colors[key_ID % 19]

        # create pattern dict
        self._pattern_dict = {}
        for key_ID in key_IDs:
            self._pattern_dict[str(key_ID)] = \
                self._all_pattern[key_ID % len(self._all_pattern)]

    def get_color(self, sched_info: Dict) -> str:
        if(self._highlight_deadline_miss
           and sched_info["deadlineMiss"]):
            return self._color_dict["deadlineMiss"]
        elif self._y_axis == "core":
            return self._color_dict[str(sched_info["taskID"])]
        elif self._y_axis == "task":
            return self._color_dict[str(sched_info["coreID"])]

    def get_pattern(self, sched_info: Dict) -> str:
        if self._y_axis == "core":
            return self._pattern_dict[str(sched_info["taskID"])]
        elif self._y_axis == "task":
            return self._pattern_dict[str(sched_info["coreID"])]


def main(src_file_path, dest_dir, y_axis, highlight_deadline_miss, draw_legend):
    with open(src_file_path) as f:
        source_dict = json.load(f)
    # TODO: validate

    quad_style_getter = QuadStyleGetter(source_dict,
                                        highlight_deadline_miss,
                                        y_axis)

    # create source_df
    source_df = pd.DataFrame(
        columns=[
            "CoreID",
            "TaskID",
            "JobID",
            "Release",
            "Deadline",
            "Start",
            "Finish",
            "Preemption",
            "Color",
            "Pattern"
        ]
    )
    for i, sched_info in enumerate(source_dict["taskSet"]):
        source_df.loc[i] = [
            sched_info["coreID"],
            sched_info["taskID"],
            sched_info["jobID"],
            sched_info["releaseTime"],
            sched_info["deadline"],
            sched_info["startTime"],
            sched_info["finishTime"],
            sched_info["preemption"],
            quad_style_getter.get_color(sched_info),
            quad_style_getter.get_pattern(sched_info)
        ]

    if y_axis == "core":
        source_df = source_df.set_index(["coreID", "taskID"])
        source_df = source_df.sort_index()

        # plot
        yaxis_list = []
        for yaxis in source_df.index.get_level_values(0).to_list():
            if yaxis not in yaxis_list:
                yaxis_list.append(yaxis)
        yaxis_list.sort(reverse=True)
        yaxis_list = ["Core " + str(y) for y in yaxis_list]

        p = figure(
            width=800,
            height=400,
            y_range=yaxis_list,
            x_range=Range1d(0, 20),
            active_scroll="wheel_zoom",
            output_backend="svg",
        )
        p.xaxis.major_label_text_font_size = "20pt"  # HACK
        p.yaxis.major_label_text_font_size = "20pt"  # HACK
        p.xaxis[0].formatter = NumeralTickFormatter(format="0,0")
        hover = HoverTool(
            tooltips="Task: @taskID<br> \
                      Job: @jobID<br>   \
                      Start: @Start<br> \
                      Finish: @Finish"
        )
        p.add_tools(hover)

        if draw_legend:
            yaxis_i = len(yaxis_list) - 1
            for _, task_df in source_df.groupby(level=0):
                for _, task_series in task_df.droplevel(0).reset_index().iterrows():
                    task_dict = task_series.to_dict()
                    task_dict = {k: [task_dict[k]] for k in task_dict.keys()}
                    source = ColumnDataSource(task_dict)
                    p.quad(
                        left="Start",
                        right="Finish",
                        bottom=yaxis_i + 0.3,
                        top=yaxis_i + 0.7,
                        source=source,
                        color="grey",
                        fill_color="Color",
                        line_color="black",
                        hatch_color="black",
                        hatch_pattern=all_pattern[
                            int(task_dict["taskID"][0]) % len(all_pattern)
                        ],
                        legend_label=f"Task {task_dict['taskID'][0]}",
                    )
                    # p.add_layout(Arrow(end=NormalHead(fill_color='black',
                    #                                 line_width=1,
                    #                                 size=10),
                    #                 x_start=task_dict['Release'][0], y_start=yaxis_i+0.7,
                    #                 x_end=task_dict['Release'][0], y_end=yaxis_i+1.0,))
                    # p.add_layout(Arrow(end=NormalHead(fill_color='black',
                    #                                 line_width=1,
                    #                                 size=10),
                    #                 x_start=task_dict['Deadline'][0], y_start=yaxis_i+1.0,
                    #                 x_end=task_dict['Deadline'][0], y_end=yaxis_i+0.7,))
                    # if(task_dict['Preemption'][0]):
                    #     p.add_layout(Arrow(end=TeeHead(line_color='red',
                    #                                 line_width=2,
                    #                                 size=10),
                    #                     line_color='red',
                    #                     line_width=2,
                    #                     x_start=task_dict['Finish'][0], y_start=yaxis_i+0.3,
                    #                     x_end=task_dict['Finish'][0], y_end=yaxis_i+0.1,))
                yaxis_i -= 1

            p.legend.click_policy = "hide"
            p.add_layout(p.legend[0], "right")

        else:
            yaxis_i = len(yaxis_list) - 1
            for _, task_df in source_df.groupby(level=0):
                source = ColumnDataSource(task_df.droplevel(0).reset_index())
                p.quad(
                    left="Start",
                    right="Finish",
                    bottom=yaxis_i + 0.3,
                    top=yaxis_i + 0.7,
                    source=source,
                    color="grey",
                    fill_color="Color",
                )
                yaxis_i -= 1

    elif y_axis == "task":
        for i, sched_info in enumerate(source_dict["taskSet"]):
            # Select color
            if highlight_deadline_miss and sched_info["deadlineMiss"]:
                color = self._color_dict["deadlineMiss"]
            else:
                color = self._color_dict[str(sched_info["coreID"])]

            source_df.loc[i] = [
                # HACK: If type of coreID is not <int>
                int(sched_info["coreID"]),
                int(sched_info["taskID"]),
                str(sched_info["jobID"]),
                sched_info["releaseTime"],
                sched_info["deadline"],
                sched_info["startTime"],
                sched_info["finishTime"],
                sched_info["preemption"],
                color,
            ]
        source_df = source_df.set_index(["taskID", "jobID"])
        source_df = source_df.sort_index()

        # plot
        yaxis_list = []
        for yaxis in source_df.index.get_level_values(0).to_list():
            if yaxis not in yaxis_list:
                yaxis_list.append(yaxis)
        yaxis_list.sort(reverse=True)
        yaxis_list = ["Task " + str(y + 1) for y in yaxis_list]

        p = figure(
            width=800,
            height=400,
            y_range=yaxis_list,
            x_range=Range1d(0, 20),
            active_scroll="wheel_zoom",
            output_backend="svg",
        )
        p.xaxis.major_label_text_font_size = "20pt"  # HACK
        p.yaxis.major_label_text_font_size = "20pt"  # HACK
        p.xaxis[0].formatter = NumeralTickFormatter(format="0,0")
        hover = HoverTool(
            tooltips="Core: @coreID<br> \
                                    Job: @jobID<br>   \
                                    Start: @Start<br> \
                                    Finish: @Finish"
        )
        p.add_tools(hover)

        if draw_legend:
            yaxis_i = len(yaxis_list) - 1
            for _, task_df in source_df.groupby(level=0):
                for _, task_series in task_df.droplevel(0).reset_index().iterrows():
                    task_dict = task_series.to_dict()
                    task_dict = {k: [task_dict[k]] for k in task_dict.keys()}
                    source = ColumnDataSource(task_dict)
                    p.quad(
                        left="Start",
                        right="Finish",
                        bottom=yaxis_i + 0.3,
                        top=yaxis_i + 0.7,
                        source=source,
                        color="grey",
                        fill_color="Color",
                        line_color="black",
                        hatch_color="black",
                        hatch_pattern=all_pattern[
                            int(task_dict["coreID"][0]) % len(all_pattern)
                        ],
                        legend_label=f"Core {task_dict['coreID'][0]}",
                    )
                    p.add_layout(
                        Arrow(
                            end=NormalHead(fill_color="black",
                                           line_width=1, size=10),
                            x_start=task_dict["Release"][0],
                            y_start=yaxis_i + 0.7,
                            x_end=task_dict["Release"][0],
                            y_end=yaxis_i + 1.0,
                        )
                    )
                    p.add_layout(
                        Arrow(
                            end=NormalHead(fill_color="black",
                                           line_width=1, size=10),
                            x_start=task_dict["Deadline"][0],
                            y_start=yaxis_i + 1.0,
                            x_end=task_dict["Deadline"][0],
                            y_end=yaxis_i + 0.7,
                        )
                    )
                    if task_dict["Preemption"][0]:
                        p.add_layout(
                            Arrow(
                                end=TeeHead(line_color="red",
                                            line_width=2, size=10),
                                line_color="red",
                                line_width=2,
                                x_start=task_dict["Finish"][0],
                                y_start=yaxis_i + 0.3,
                                x_end=task_dict["Finish"][0],
                                y_end=yaxis_i + 0.1,
                            )
                        )
                yaxis_i -= 1

            p.legend.click_policy = "hide"
            p.add_layout(p.legend[0], "right")

    output_file(
        f"{dest_dir}/{os.path.splitext(os.path.basename(src_file_path))[0]}.html"
    )
    save(p)


if __name__ == "__main__":
    src_file_path, dest_dir, y_axis, highlight_deadline_miss, draw_legend = option_parser()
    main(src_file_path, dest_dir, y_axis,
         highlight_deadline_miss, draw_legend)
