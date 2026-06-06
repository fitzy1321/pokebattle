-- Check for NULL sprites
SELECT * FROM dex_pokemon where front_sprite = NULL OR back_sprite = NULL;

-- Get all moves from a pokemon's id.
SELECT * FROM dex_move dm
join dex_pokemon_moves dpm ON dm.id = dpm.move_id
where dpm.pokemon_id = ?;
