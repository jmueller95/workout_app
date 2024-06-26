import argparse
import json
from gtts import gTTS
from random import sample
from pydub import AudioSegment  # You need ffmpeg for this to work
import os

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import time
import string

SOUND_FRAMERATE = 20000

punctuation_table = str.maketrans(dict.fromkeys(string.punctuation))


def printAndSpeak(command, sleep_time=0.0, command_end="\n\n"):
    """
    :param command: An element either from the list of exercises or from the list of miscellaneous commands
    :param sleep_time: Time in seconds to wait for playback of the command (useful if next spoken command comes right after)
    :param command_end: By default, a printed command ends with 2 newlines, but sometimes you might want to have sth else
    """
    print(command['text'], end=command_end)
    pygame.mixer_music.load(command['audio'])
    pygame.mixer_music.play()
    time.sleep(sleep_time)


def countdown(misc_data):
    """
    :param misc_data: The list of 'miscellaneous' commands from the data dictionary
    """
    printAndSpeak(misc_data['3'], 1, "... ")
    printAndSpeak(misc_data['2'], 1, "... ")
    printAndSpeak(misc_data['1'], 1, "...\n\n")


def getArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", type=str)
    parser.add_argument("-e", '--n_exercises', type=int)
    parser.add_argument("-s", '--sets', type=int)
    parser.add_argument("-l", '--set_length', type=int)
    parser.add_argument("-d", '--exercise_duration', type=int)
    parser.add_argument("-b", '--break_duration', type=int)
    return parser.parse_args()


def loadNewAudio(data):
    is_data_changed = False
    for entry in data['exercises'] + list(data['miscellaneous'].values()):
        if 'audio' not in entry or not entry['audio']:
            is_data_changed = True
            print("Generating Audio Track for '{}'...".format(entry['text']))
            # gTTS can only generate MP3, but PyGame has issues with this format...
            speech = gTTS(text=entry['text'], lang=entry.get('language', "de"), slow=False)
            filepath_base = "{}".format(
                os.path.join(data['audio_folder'],
                             entry['text'].lower().translate(punctuation_table).replace(" ", "_")))
            speech.save("{}.mp3".format(filepath_base))
            # ...so we convert it to Wave afterwards...
            AudioSegment.from_mp3("{}.mp3".format(filepath_base)).set_frame_rate(SOUND_FRAMERATE).export(
                "{}.wav".format(filepath_base), format="wav")
            # ...and delete the MP3
            os.remove("{}.mp3".format(filepath_base))
            entry['audio'] = "{}.wav".format(filepath_base)

    if is_data_changed:
        print("\n\n")
    with open("exercises.json", "w") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)


def createHIITExerciseList(data, n_exercises):
    # The number of exercises needs to be divisible by three
    if (remainder := n_exercises % 3) > 0:
        n_exercises -= remainder
        print("For HIIT, the number of exercises needs to be a multiple of three.\n"
              "Effective number of exercises will be {}.".format(n_exercises))
    low_intensity_pool = [ex for ex in data['exercises'] if 'warmup' in ex['categories']]
    high_intensity_pool = [ex for ex in data['exercises'] if 'hiit' in ex['categories']]
    low_intensity_list = sample(low_intensity_pool, min(len(low_intensity_pool), int(n_exercises * 2 / 3)))
    high_intensity_list = sample(high_intensity_pool, min(len(high_intensity_pool), int(n_exercises * 1 / 3)))
    # Now we zip the two lists 2:1 so that two low-intensity exercises are alternating with one high-intensity exercise
    res = []
    for i in range(len(high_intensity_list)):
        res.append(low_intensity_list[2 * i])
        res.append(low_intensity_list[2 * i + 1])
        res.append(high_intensity_list[i])
    return res


# exercise_pool = [ex for ex in data['exercises'] if args.mode in ex['categories']]
# exercise_list = sample(exercise_pool, min(len(exercise_pool), args.n_exercises))


def main():
    full_start_time = time.time()  ##DEBUG
    args = getArguments()

    if args.mode.lower() == "hiit":
        # We internally have only one set in HIIT, so we multiply the set length by the number of sets given by the user
        args.set_length *= args.sets
        args.sets = 1
        args.break_duration = 0

    # Load all exercises
    with open("exercises.json") as infile:
        data = json.load(infile)

    # Add audio for all exercises where audio is null and, if add the new audiofile paths to the json file
    loadNewAudio(data)

    # Now we construct the list of exercises
    if args.mode.lower() == "hiit":
        # HIIT is a special case because we will have to prepare two pools of exercises.
        # So this deserves its own function.
        exercise_list = createHIITExerciseList(data, args.n_exercises)
    else:
        # Otherwise, we filter for the selected category and randomly choose 'n_exercises' exercises in random order
        exercise_pool = [ex for ex in data['exercises'] if args.mode in ex['categories']]
        exercise_list = sample(exercise_pool, min(len(exercise_pool), args.n_exercises))

    workout_duration_seconds = args.sets * (
            args.set_length * args.exercise_duration + args.break_duration) - args.break_duration
    transition_duration_seconds = args.sets * (
            5 + args.set_length * 5 + len([ex for ex in exercise_list if ex['is_chiral']]))

    print(
        "Du hast folgendes Workout gewählt: {}, {} Sets, bestehend aus je {} Übungen, Gesamtdauer (inkl. Übergänge): Circa {} Minuten.\n".format(
            args.mode.capitalize(), args.sets, args.set_length,
            ((workout_duration_seconds + transition_duration_seconds) // 60 + 1)) +
        "Deine Übungen für Heute:\n\t{}\n".format("\n\t".join([ex['text'] for ex in exercise_list])))
    # Give the athlete some seconds to read this text
    time.sleep(5)
    # Initiate the sound output engine
    pygame.init()
    pygame.mixer.init(frequency=SOUND_FRAMERATE)
    printAndSpeak(data['miscellaneous']['workout_start'], 1.5)
    exercise_index = 0
    # 'Set' Logic: Announce the beginning of each set until the number of sets is reached. Then the workout ends.
    for set_index in range(1, args.sets + 1):
        printAndSpeak(data['miscellaneous']['set'], 0.75, " ")
        printAndSpeak(data['miscellaneous'][str(set_index)], 0.5, " ")
        printAndSpeak(data['miscellaneous']['of'], 0.75, " ")
        printAndSpeak(data['miscellaneous'][str(args.sets)], 1.5)

        # 'Exercise' Logic: Announce exercise after exercise until the 'set length' is reached and it is time for a break
        for exercise_index_within_current_set in range(args.set_length):
            # Announce name of current exercise and wait some seconds before starting it
            printAndSpeak(exercise_list[exercise_index], 5)
            # Start exercise and wait until there are 10 seconds left - except if it is chiral
            # If it's chiral, command 'change sides' after half of the exercise's duration
            duration_until_announcement = args.exercise_duration - 10 if not exercise_list[exercise_index][
                'is_chiral'] else args.exercise_duration / 2

            printAndSpeak(data['miscellaneous']['exercise_start'],
                          duration_until_announcement)
            if exercise_list[exercise_index]['is_chiral']:
                printAndSpeak(data['miscellaneous']['change_sides'], 5)
                printAndSpeak(data['miscellaneous']['continue'], (args.exercise_duration / 2) - 10)
            # Set index to next exercise in list (reset in case it reaches the end of the list)
            exercise_index = exercise_index + 1 if exercise_index + 1 < len(exercise_list) else 0
            # Announce next exercise and wait until there are 3 seconds left - except if there's a break coming up
            printAndSpeak(data['miscellaneous']['next'], 1.5,
                          " ") if exercise_index_within_current_set < args.set_length - 1 else time.sleep(1.5)
            printAndSpeak(exercise_list[exercise_index],
                          5.5) if exercise_index_within_current_set < args.set_length - 1 else time.sleep(5.5)
            # Countdown to exercise end
            countdown(data['miscellaneous'])
        # 'Break' Logic - after the set length is reached, make a break unless it is the last set
        if set_index < args.sets:
            printAndSpeak(data['miscellaneous']['break'], args.break_duration - 10)
            # Announce next exercise and wait until there are 3 seconds left
            printAndSpeak(data['miscellaneous']['next'], 1.5, " ")
            printAndSpeak(exercise_list[exercise_index], 5.5)
            # Countdown to break end
            countdown(data['miscellaneous'])
    # We arrive here after the end of the last set.
    printAndSpeak(data['miscellaneous']['workout_end'], 3)

    print("Gesamtdauer: {} m {} s".format(workout_duration_seconds // 60, workout_duration_seconds % 60))
    time_elapsed = time.time() - full_start_time  # DEBUG
    print("Gemessene Zeit: {} m {} s".format(time_elapsed // 60, time_elapsed % 60))  # DEBUG


if __name__ == '__main__':
    main()
