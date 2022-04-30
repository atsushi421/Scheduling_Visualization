import random
import argparse
import json
import os
import pandas as pd

from bokeh.plotting import figure, output_file, save, show
from bokeh.models import (
    ColumnDataSource,
    Range1d,
    NumeralTickFormatter,
    Arrow,
    NormalHead,
    OpenHead,
    VeeHead,
    TeeHead
)
from bokeh.models.tools import HoverTool
from bokeh.palettes import d3, grey

pattern = [
    ' ',
    '.',
    'o',
    '-',
    '|',
    '+',
    '"',
    ':',
    '@',
    '/',
    '\\',
    'x',
    ',',
    '`',
    'v',
    '>',
    '*'
]


def option_parser() -> str:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-s', '--source_file_path',
                            required=True,
                            type=str,
                            help='The path to source json file')
    arg_parser.add_argument('-d', '--dest_dir',
                            required=True,
                            type=str,
                            help='The path to dest result file')
    arg_parser.add_argument('-hdm', '--highlight_deadline_miss',
                            required=False,
                            action='store_true',
                            help='Highlight tasks in which deadline errors occurred')
    arg_parser.add_argument('-l', '--draw_legend',
                            required=False,
                            action='store_true',
                            help='Draw a legend for each task')
    args = arg_parser.parse_args()

    return args.source_file_path, args.dest_dir, args.highlight_deadline_miss, args.draw_legend


def get_color_dict(source_dict: dict, highlight_deadline_miss: bool) -> dict:
    # get taskIDs
    taskIDs = set()
    for task in source_dict['taskSet']:
        taskIDs.add(task['taskID'])
    taskIDs = sorted(list(taskIDs))

    # create color dict
    color_dict = {}
    if(highlight_deadline_miss):
        color_dict['deadlineMiss'] = 'red'
        greys = grey(len(taskIDs) + 2)
        for taskID in taskIDs:
            color_dict[str(taskID)] = greys[taskID + 1]
    else:
        colors = d3['Category20'][20]
        for taskID in taskIDs:
            color_dict[str(taskID)] = colors[taskID % 19]

    return color_dict


def main(source_file_path, dest_dir, highlight_deadline_miss, draw_legend):
    ### json -> df
    with open(source_file_path) as f:
        source_dict = json.load(f)
    source_df = pd.DataFrame(columns=['coreID',
                                      'taskID',
                                      'jobID',
                                      'Release',
                                      'Deadline',
                                      'Start',
                                      'Finish',
                                      'Preemption',
                                      'Color'])
    color_dict = get_color_dict(source_dict, highlight_deadline_miss)

    for i, task in enumerate(source_dict['taskSet']):
        # Select color
        if(highlight_deadline_miss and task['deadlineMiss']):
            color = color_dict['deadlineMiss']
        else:
            color = color_dict[str(task['taskID'])]
        
        source_df.loc[i] = [int(task['coreID']),  # HACK: If type of coreID is not <int>
                            str(task['taskID']),
                            str(task['jobID']),
                            task['releaseTime'],
                            task['deadline'],
                            task['startTime'],
                            task['finishTime'],
                            task['preemption'],
                            color]
    source_df = source_df.set_index(["coreID", "taskID"])
    source_df = source_df.sort_index()

    # plot
    yaxis_list = []
    for yaxis in source_df.index.get_level_values(0).to_list():
        if(yaxis not in yaxis_list):
            yaxis_list.append(yaxis)
    yaxis_list.sort(reverse=True)
    yaxis_list = ['Core '+str(y) for y in yaxis_list]

    p = figure(width=800,height=400,
               y_range=yaxis_list,
               x_range=Range1d(0, 20),
               active_scroll='wheel_zoom',
               output_backend='svg')
    p.xaxis.major_label_text_font_size = '20pt'  # HACK
    p.yaxis.major_label_text_font_size = '20pt'  # HACK
    p.xaxis[0].formatter = NumeralTickFormatter(format='0,0')
    hover = HoverTool(tooltips="Task: @taskID<br> \
                                Job: @jobID<br>   \
                                Start: @Start<br> \
                                Finish: @Finish")
    p.add_tools(hover)

    if(draw_legend):
        yaxis_i = len(yaxis_list) - 1
        for _, task_df in source_df.groupby(level=0):
            for _, task_series in task_df.droplevel(0).reset_index().iterrows():
                task_dict = task_series.to_dict()
                task_dict = {k: [task_dict[k]] for k in task_dict.keys()}
                source = ColumnDataSource(task_dict)
                p.quad(left='Start',
                       right='Finish',
                       bottom=yaxis_i+0.3,
                       top=yaxis_i+0.7,
                       source=source,
                       color='grey',
                       fill_color='Color',
                       line_color='black',
                       hatch_color='black',
                       hatch_pattern=pattern[int(task_dict['taskID'][0]) % len(pattern)],
                       legend_label=f"Task {task_dict['taskID'][0]}")
                p.add_layout(Arrow(end=NormalHead(fill_color='black',
                                                  line_width=1,
                                                  size=10),
                                   x_start=task_dict['Release'][0], y_start=yaxis_i+0.7,
                                   x_end=task_dict['Release'][0], y_end=yaxis_i+1.0,))
                p.add_layout(Arrow(end=NormalHead(fill_color='black',
                                                  line_width=1,
                                                  size=10),
                                   x_start=task_dict['Deadline'][0], y_start=yaxis_i+1.0,
                                   x_end=task_dict['Deadline'][0], y_end=yaxis_i+0.7,))
                if(task_dict['Preemption'][0]):
                    p.add_layout(Arrow(end=TeeHead(line_color='red',
                                                  line_width=2,
                                                  size=10),
                                       line_color='red',
                                       line_width=2,
                                       x_start=task_dict['Finish'][0], y_start=yaxis_i+0.3,
                                       x_end=task_dict['Finish'][0], y_end=yaxis_i+0.1,))
            yaxis_i -= 1

        p.legend.click_policy = 'hide'
        p.add_layout(p.legend[0], 'right')

    else:
        yaxis_i = len(yaxis_list) - 1
        for _, task_df in source_df.groupby(level=0):
            source = ColumnDataSource(task_df.droplevel(0).reset_index())
            p.quad(left='Start',
                right='Finish',
                bottom=yaxis_i+0.3,
                top=yaxis_i+0.7,
                source=source,
                color='grey',
                fill_color='Color')

            yaxis_i -= 1

    output_file(f'{dest_dir}/{os.path.splitext(os.path.basename(source_file_path))[0]}.html')
    save(p)


if __name__ == '__main__':
    source_file_path, dest_dir, highlight_deadline_miss, draw_legend = option_parser()
    main(source_file_path, dest_dir, highlight_deadline_miss, draw_legend)
