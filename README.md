```shell
git clone --no-checkout git@github.com:raytheonbbn/maude-hcs.git experiments/
git submodule absorbgitdirs experiments/
git submodule init experiments/
git -C experiments/ config core.sparseCheckout true
git -C experiments/ sparse-checkout set --no-cone "use-cases/challenge-problem-4"
git submodule update --force experiments/
```
