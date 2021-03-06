class Options():
    """Represents the options used to control an experimental run."""

    def __init__(self, options):
        if 'train_stages' in options and options['train_stages'] is not None:
            train_stages = options['train_stages']
            options.update(train_stages[0])
        self.train_stages = options.get('train_stages')

        # Required options
        self.problem_type = options['problem_type']
        self.model_type = options['model_type']
        self.run_name = options['run_name']
        self.dataset_name = options['dataset_name']
        self.generator_name = options['generator_name']
        self.batch_size = options['batch_size']
        self.epochs = options['epochs']
        self.steps_per_epoch = options['steps_per_epoch']
        self.validation_steps = options['validation_steps']
        self.active_input_inds = options['active_input_inds']

        # Optional options
        self.git_commit = options.get('git_commit')
        # Size of the imgs used as input to the network
        # [nb_rows, nb_cols]
        self.target_size = options.get('target_size', (256, 256))
        self.optimizer = options.get('optimizer', 'adam')
        self.init_lr = options.get('init_lr', 1e-3)
        self.patience = options.get('patience')
        self.lr_schedule = options.get('lr_schedule')
        self.train_ratio = options.get('train_ratio')
        self.cross_validation = options.get('cross_validation')
        self.delta_model_checkpoint = options.get(
            'delta_model_checkpoint', None)
