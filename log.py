import logging

log=logging.Logger(__name__)
log_file=logging.FileHandler('logfile.txt')
log_console=logging.StreamHandler()
log_format=logging.Formatter('%(asctime)-15s [%(levelname)s] %(message)s')
log_file.setFormatter(log_format)
log_file.setLevel(logging.WARNING)
log_console.setFormatter(log_format)
log_console.setLevel(logging.INFO)
log.addHandler(log_file)
log.addHandler(log_console)
