# Pokémon Battle System

I thought I'd build a silly project.

I want to replicate a turn based monster fighting system, the back and forth, type based advantage, status effects, etc.

oI'll probably go with gen 1 - 3, since that's what I played, and I'm not trying to accuratley simulate anything.

**THIS IS A FUNNY PROJECT. USE AT YOUR OWN RISK!!**

## Requirements

I need static pokemon data like base stats species id etc, move list, and a learn set per pokemon.

I'm still debating having static pokemon data in csv files, or in a sqlite db along with user instance data?

But I also need user instance pokemon data, which ones are in the party, what level, what moves, status effects, etc. Also need user data for a bag/inventory system eventually.

sqlite might be the easiest solution, idk if it's the best but it works.

For the actual battles, I want to implement strategy pattern in C, but I'm not sure how yet. Probably higher order functions and function pointers, oi. I'm still learning the nitty-gritty of C, so we'll see how this evolves.

- [ ] C sqlite library
- [ ] C unit testing
- [ ] Static Pokemon Data (attack, defense, speed, special, evolution_level, next_pokemon_id)
- [ ] Static Global Move List (name, base pp, base damage, status effects, stages, etc)
- [ ] Static Species Learn set (pokemon_id, move_id, level=>=1, type=["level up","tm","hm","tutor","egg", etc])
- [ ] User party pokemon data
- [ ] Enemy party pokemon data
- [ ] Strategy pattern in C, for the battle system (after other objects have been written)

## Data

Using https://pokeapi.co and python to fetch and transform data from json to sqlite. Still in progress.
