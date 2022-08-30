import argparse
import json
import os
from typing import Dict, List

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


class QuadSourceGenerator():
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

        # get coreIDs & taskIDs
        taskIDs = set()
        coreIDs = set()
        for task in source_dict["taskSet"]:
            taskIDs.add(task["taskID"])
            coreIDs.add(task["coreID"])
        self._taskIDs = sorted(list(taskIDs), reverse=True)
        self._taskID_offset = self._taskIDs[-1]
        self._coreIDs = sorted(list(coreIDs), reverse=True)
        self._coreID_offset = self._coreIDs[-1]

        # create color dict & pattern dict
        if self._y_axis == "core":
            key_IDs = self._taskIDs
        elif self._y_axis == "task":
            key_IDs = self._coreIDs
        else:
            raise NotImplementedError()

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

        self._pattern_dict = {}
        for key_ID in key_IDs:
            self._pattern_dict[str(key_ID)] = \
                self._all_pattern[key_ID % len(self._all_pattern)]

    def get_y_axis_list(self) -> List[str]:
        if self._y_axis == "core":
            y_axis_list = [f"Core {coreID}" for coreID in self._coreIDs]
        elif self._y_axis == "task":
            y_axis_list = [f"Task {taskID}" for taskID in self._taskIDs]

        return y_axis_list

    def get_y_base(self, ID: int) -> int:
        if self._y_axis == "core":
            y_base = (self._coreIDs[ID - self._coreID_offset]
                      - self._coreID_offset)
        elif self._y_axis == "task":
            y_base = (self._taskIDs[ID - self._taskID_offset]
                      - self._taskID_offset)

        return y_base

    def generate(self, sched_info: Dict) -> ColumnDataSource:
        if self._y_axis == "core":
            y_base = self.get_y_base(sched_info["coreID"])
            color = self._color_dict[str(sched_info["taskID"])]
            hatch_pattern = self._pattern_dict[str(sched_info["taskID"])]
            legend_label = f'Task {sched_info["taskID"]}'
        elif self._y_axis == "task":
            y_base = self.get_y_base(sched_info["taskID"])
            color = self._color_dict[str(sched_info["coreID"])]
            hatch_pattern = self._pattern_dict[str(sched_info["coreID"])]
            legend_label = f'Core {sched_info["coreID"]}'

        if(self._highlight_deadline_miss
           and sched_info["deadlineMiss"]):
            color = self._color_dict["deadlineMiss"]

        quad_source_dict = {
            "Left": [sched_info["startTime"]],
            "Right": [sched_info["finishTime"]],
            "Bottom": [y_base + 0.3],
            "Top": [y_base + 0.7],
            "Color": ["grey"],
            "FillColor": [color],
            "LineColor": ["black"],
            "HatchColor": ["black"],
            "HatchPattern": [hatch_pattern],
            "LegendLabel": [legend_label],
        }

        if sched_info.get("jobID"):
            quad_source_dict["JobID"] = [f'Job {sched_info["jobID"]}']

        return ColumnDataSource(data=quad_source_dict)


def main(
    src_file_path,
    dest_dir,
    y_axis,
    highlight_deadline_miss,
    draw_legend
) -> None:
    with open(src_file_path) as f:
        source_dict = json.load(f)
    # TODO: validate

    quad_source_generater = QuadSourceGenerator(source_dict,
                                                highlight_deadline_miss,
                                                y_axis)

    # preprocessing for plot
    p = figure(
        width=800,
        y_range=quad_source_generater.get_y_axis_list(),
        x_range=Range1d(0, source_dict["makespan"]),
        active_scroll="wheel_zoom",
        output_backend="svg",
    )
    hover = HoverTool(
        tooltips="@LegendLabel<br> \
                  @JobID<br> \
                  Start: @Left<br> \
                  Finish: @Right"
    )
    p.sizing_mode = 'stretch_both'
    p.xaxis.major_label_text_font_size = "20pt"  # HACK
    p.yaxis.major_label_text_font_size = "20pt"  # HACK
    p.xaxis[0].formatter = NumeralTickFormatter(format="0,0")
    p.add_tools(hover)

    # plot
    for sched_info in source_dict["taskSet"]:
        quad_source = quad_source_generater.generate(sched_info)
        p.quad(
            source=quad_source,
            left="Left",
            right="Right",
            bottom="Bottom",
            top="Top",
            color="Color",
            fill_color="FillColor",
            line_color="LineColor",
            hatch_color="HatchColor",
            hatch_pattern="HatchPattern",
            legend_label=f'{quad_source.data["LegendLabel"][0]}'
        )

        # plot other symbols
        if y_axis == "task":
            if isinstance(sched_info.get("releaseTime"), int):
                p.add_layout(
                    Arrow(
                        end=NormalHead(fill_color="black",
                                       line_width=1, size=6),
                        x_start=sched_info["releaseTime"],
                        y_start=quad_source_generater.get_y_base(
                            sched_info["taskID"]) + 0.7,
                        x_end=sched_info["releaseTime"],
                        y_end=quad_source_generater.get_y_base(
                            sched_info["taskID"]) + 1.0,
                    )
                )
            if sched_info.get("deadline"):
                p.add_layout(
                    Arrow(
                        end=NormalHead(fill_color="black",
                                       line_width=1, size=6),
                        x_start=sched_info["deadline"],
                        y_start=quad_source_generater.get_y_base(
                            sched_info["taskID"]) + 1.0,
                        x_end=sched_info["deadline"],
                        y_end=quad_source_generater.get_y_base(
                            sched_info["taskID"]) + 0.7,
                    )
                )
            if sched_info.get("preemption"):
                p.add_layout(
                    Arrow(
                        end=TeeHead(line_color="red",
                                    line_width=2, size=6),
                        line_color="red",
                        line_width=2,
                        x_start=sched_info["finishTime"],
                        y_start=quad_source_generater.get_y_base(
                            sched_info["taskID"]) + 0.7,
                        x_end=sched_info["finishTime"],
                        y_end=quad_source_generater.get_y_base(
                            sched_info["taskID"]) + 1.0,
                    )
                )

    p.legend.click_policy = "hide"
    p.add_layout(p.legend[0], "right")

    # output
    output_file(
        f"{dest_dir}/"
        f"{os.path.splitext(os.path.basename(src_file_path))[0]}.html"
    )
    save(p)


if __name__ == "__main__":
    (src_file_path, dest_dir, y_axis,
     highlight_deadline_miss, draw_legend) = option_parser()
    main(src_file_path, dest_dir, y_axis,
         highlight_deadline_miss, draw_legend)
