```shell
git clone --filter=blob:none --no-checkout git@github.com:raytheonbbn/maude-hcs.git experiments/
git -C experiments/ sparse-checkout set --no-cone "use-cases/challenge-problem-4"
git -C experiments/ checkout
git submodule add -b <branch> git@github.com:raytheonbbn/maude-hcs.git  experiments/
git checkout <branch>
```
