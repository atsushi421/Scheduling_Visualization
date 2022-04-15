import random
import argparse
import json
import os
import pandas as pd

from bokeh.plotting import figure, output_file, save
from bokeh.models import ColumnDataSource, Range1d, NumeralTickFormatter
from bokeh.models.tools import HoverTool
from bokeh.palettes import d3

colors = d3['Category20'][20]


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
    args = arg_parser.parse_args()

    return args.source_file_path, args.dest_dir, args.highlight_deadline_miss


def main(source_file_path, dest_dir, highlight_deadline_miss):
    # json -> df
    with open(source_file_path) as f:
        source_dict = json.load(f)
    source_df = pd.DataFrame(columns=['coreID', 'taskID', 'Start', 'End', 'Color'])
    for i, task in enumerate(source_dict['taskSet']):
        # Select color
        if(highlight_deadline_miss):
            if('deadlineMiss' in task.keys()):
                color = 'red'
            else:
                color = '#DCDCDC'
        else:
            color = colors[random.randint(0, 19)]
        
        source_df.loc[i] = [int(task['coreID']),  # HACK: If type of coreID is not <int>
                            str(task['taskName']),
                            task['startTime'],
                            task['startTime']+task['executionTime'],
                            color]
    source_df = source_df.set_index(["coreID", "taskID"])
    source_df = source_df.sort_index()

    # plot
    yaxis_list = []
    for yaxis in  source_df.index.get_level_values(0).to_list():
        if(yaxis not in yaxis_list):
            yaxis_list.append(yaxis)
    yaxis_list.sort(reverse=True)
    yaxis_list = ['Core '+str(y) for y in yaxis_list]

    p = figure(width=800,height=400,
               y_range=yaxis_list,
               x_range=Range1d(0, source_dict['makespan']),
               active_scroll='wheel_zoom',
               output_backend='svg')
    p.xaxis[0].formatter = NumeralTickFormatter(format='0,0')
    hover = HoverTool(tooltips="Task: @taskID<br> \
                                Start: @Start<br> \
                                End: @End")
    p.add_tools(hover)

    yaxis_i = len(yaxis_list) - 1
    for _, task_df in source_df.groupby(level=0):
        source = ColumnDataSource(task_df.droplevel(0))
        p.quad(left='Start',
               right='End',
               bottom=yaxis_i+0.3,
               top=yaxis_i+0.7,
               source=source,
               color='grey',
               fill_color='Color')
        yaxis_i -= 1

    output_file(f'{dest_dir}/{os.path.splitext(os.path.basename(source_file_path))[0]}.html')
    save(p)


if __name__ == '__main__':
    source_file_path, dest_dir, highlight_deadline_miss = option_parser()
    main(source_file_path, dest_dir, highlight_deadline_miss)
