"""
app/robot/homing.py
Module de compatibilité redirigeant vers app/robot/recalage.py.
Conserve la compatibilité avec tout code important les noms historiques en anglais.
"""

from app.robot.recalage import (
    attendre_fin_mouvement,
    wait_until_motion_finished,
    executer_sequence_recalage,
    run_homing_sequence
)
