import argparse
import json
import sys
import os
import math

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('data', help='JSON file containing Aesprite animation data')
    parser.add_argument('dest', help='destination path for outout C files')

    args = parser.parse_args()

    name = os.path.basename(args.data).split('.')[0]
    data = json.loads(open(args.data).read())

    # map the frames into an array (technically it's an object / dict but lets assume it's ordered and sorted already :)
    frames = [frame for _, frame in data['frames'].items()]

    # calculate the identifiers and data we'll use across the source files
    codegen_data = {
        'object': f'{name}_animation',
        'struct': f'{name.capitalize()}AnimationState',
        'enum': f'{name.capitalize()}Animations',
        'animations': [{**tag, 'enum_member': tag['name'].upper(), 'timings': calculate_animation_timing(tag, frames)} for tag in data['meta']['frameTags']],
    }

    # create C files at the destination
    open(f'{args.dest}/{name}_animation.h', 'w+').write(generate_header(**codegen_data))
    open(f'{args.dest}/{name}_animation.c', 'w+').write(generate_code(**codegen_data))


def calculate_animation_timing(animation, frames):
    # return a list of 2-tuples representing the tile index and number of frames to stay there, and the total frames of the animation
    animationFrames = frames[animation['from']:animation['to']+1]

    if (animation['direction'] == 'pingpong'):
        animationFrames += frames[animation['to'] -1 : animation['from'] : -1]

    totalFrames = 0
    frameTimings = []

    for frame in animationFrames:
        tid = int((frame['frame']['x'] / frame['sourceSize']['w']) * (frame['sourceSize']['w'] * frame['sourceSize']['h'] / 64)) # todo support more bitdepths / tile sizes
        frameDuration = int(math.floor(frame['duration'] / 16)) # 16 is approximate ms / frame @ 60fps
        totalFrames += frameDuration
        frameTimings.append((tid, totalFrames))
        
    
    return (totalFrames, frameTimings)
    
    
def generate_header(object, enum, struct, animations):
    # open header guard
    hcode = f'#ifndef {object.upper()}_ANIMATION_H\n#define {object.upper()}_ANIMATION_H\n\n'

    #include tonc header
    hcode +='#include <tonc.h>\n\n'

    # define an enumeration for the animations

    hcode += f'typedef enum {{\n'

    for animation in animations:
        enum_member = animation['enum_member']
        hcode += f'\t{enum_member},\n'

    hcode += f'}} {enum};\n\n'

    #define a struct for the current animation state

    hcode += f'typedef struct {{\n'
    hcode += '\tOBJ_ATTR *obj; // pointer to the sprite object in GBA memory\n'
    hcode += f'\t{enum} current_animation;\n'
    hcode += f'\tint timer; // number of frames the current animation has been playing\n'
    hcode += f'}} {struct};\n\n'

    # declare the update function
    hcode += f'void update_{object}({struct} * state);\n\n'

    # declare start functions for each animation
    for animation in animations:
        name = animation['name']
        hcode += f'void start_{name}({struct} * state);\n\n'

    # close the header guard  
    hcode += f'#endif // {object.upper()}_ANIMATION_H\n'

    return hcode


def generate_code(object, enum, struct, animations):
    ccode = f'#include \"{object}.h\"\n\n'

    # define the update function
    ccode += f'void update_{object}({struct} * state) {{\n\n'

    # switch on animation state
    ccode += f'\tswitch (state->current_animation) {{\n'

    for animation in animations:
        enum_member = animation['enum_member']
        total_duration, frameTimings = animation['timings']
        ccode += f'\t\tcase {enum_member}:\n'

        # naive animation control logic for now: pile of IFs lets goooooo
        for tid, timing in frameTimings:
            ccode += f'\t\t\tif ((state->timer % {total_duration}) < {timing}) {{ state->obj->attr2 = ATTR2_PALBANK(0) | {tid}; break; }}\n' # todo suport other shapes

        ccode += f'\t\t\tbreak;\n'

    ccode+= '\t}\n\n' # close switch

    ccode += '\tstate->timer++;\n' # increment the animation timer

    ccode+= '}\n\n' # close update function

    # define the start functions
    for animation in animations:
        name = animation['name']
        enum_member = animation['enum_member']
        ccode += f'void start_{name}({struct} * state) {{\n\n'
        ccode += f'\tstate->current_animation = {enum_member};\n'
        ccode += '\tstate->timer = 0;\n'
        ccode += '}\n\n'

    return ccode


if __name__ == '__main__':
    sys.exit(main())