from jinja2 import Environment, FileSystemLoader
import argparse
import json
import sys
import math

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('data', help='JSON file containing Aesprite animation data')
    parser.add_argument('dest', help='destination path for outout C files')
    args = parser.parse_args()

    # Load the animation data file
    with open(args.data, 'r') as json_file:
        data = json.loads(json_file.read())

    # map the frames into an array (technically it's an object / dict but lets assume it's ordered and sorted already :)
    frames = [frame for _, frame in data['frames'].items()]

    animation = {
        'name': data['meta']['image'].split('.')[0],
        'tags': [{**tag, 'timing': calculate_timing(tag, frames)} for tag in data['meta']['frameTags']]
    }

    # load the template
    env = Environment(loader=FileSystemLoader('./templates'), trim_blocks=True, lstrip_blocks=True)

    template = env.get_template('animation_header_template.jinja2')

    output = template.render(animation=animation)

    # Save the rendered output to a file
    with open(f'{args.dest}/{animation['name']}_animation.h', 'w+') as c_file:
        c_file.write(output)

    # load the implementation template

    template = env.get_template('animation_implementation_template.jinja2')

    output = template.render(animation=animation)

    # Save the rendered output to a file
    with open(f'{args.dest}/{animation['name']}_animation.c', 'w+') as c_file:
        c_file.write(output)



def calculate_timing(tag, frames):

    tagFrames = frames[tag['from']:tag['to']+1]

    if (tag['direction'] == 'pingpong'):
        tagFrames += frames[tag['to'] -1 : tag['from'] : -1]

    totalFrames = 0
    frameTimings = []

    for frame in tagFrames:
        tid = int((frame['frame']['x'] / frame['sourceSize']['w']) * (frame['sourceSize']['w'] * frame['sourceSize']['h'] / 64)) # todo support more bitdepths / tile sizes
        frameDuration = int(math.floor(frame['duration'] / 16)) # 16 is approximate ms / frame @ 60fps
        totalFrames += frameDuration
        frameTimings.append({
            'tid': tid, 
            'lastFrame': totalFrames 
        })
    
    return {
        'totalFrames': totalFrames,
        'frameTimings': frameTimings
    }
    
    

if __name__ == '__main__':
    sys.exit(main())