J'ai un projet: un script qui crée des vidéos simple à l'aide de l'IA


Les étapes du processus sont


Création de texte a l'aide d'un bon prompt (avec possibilité de tout modifier juste avec le titre de la vidéo genre on dit a l'IA tu dois fait ceci cela et le titre de la vidéo est : et on va entrer le titre.)


Et si on ne veux pas donner le titre, par défaut on va donner un prompt différent qui dira a l'IA de choisir le texte lui même 


L'étape suivante sera le text to speech avec une IA locale que l'on aura pris sur huggin face, ou une API


L'étape 3 sera le montage avec un set de vidéo que l'on pourra placer aléatoirement les unes a la suite des autres (une idée d'amélioration a la quelle je pense est d'utiliser une API ou un truc du genre pour prendre une vidéo adapté à la phrase en ligne. Ou alors l'utilisation d'une IA de génération d'images (si la première proposition n'est pas possible ou alors si on veut générer des images très spécifique). J'aimerais que tu pars sur internet pour explorer ses pistes et voir si c'est possible)


L'étape suivante c'est les sous-titres avec une IA speech to text qui va détecter a quelle moment chaque mot est dit et que vas les afficher a l'écran avec ffmpeg pour une synchronisation parfaite.


L'étape suivante est optionnel (uniquement pour le format long youtube) avec une IA de génération d'images. le prompt de cet IA sera donné par une IA de type LLM qui va utiliser le titre et le contenu de la vidéo pour donner un prompt concis et précis a l'IA de génération d'images (local ou avec une API)


L'étape suivante c'est l'upload avec l'API de youtube.(Faudra pas utiliser une IA pour générer la description)


On pourra optionnelement stocker les vidéos localement (en utilisant leur titre comme nom de fichier) et pendant le développement il faut un dossier temp associé au vidéo avec tout les fichiers intermédiaire créé (le script, la vidéo sans sous titre, (et d'autres fichiers dis moi les quel tu penses qu'il seront))


J'hésite pour le langage de programmation (entre rust et python, je veux que tu me donnes des conseils)


Je veux que l'interface soit une sorte de TUI dans le terminal, mais que si on veuille le convertir en app (linux, windows et mac in puisse le faire)

(Propose moi des stack technique)


Je veux une jolie phase de setup. Dans le terminal ça pourrait ressembler à ça :


- bienvenue sur auto-video

- choisissez l'IA qui va faire le script des vidéos 

- en ligne local ou les deux 

- si on choisi en ligne on donne le provider

- ensuite la clé d'api

- ensuite le modèle 

- ensuite on peut choisir d'ajouter un modèle 

- si l'user dit non on lui propose d'ajouter un nouveau provider

- si il dit non étape suivante 

- pour l'option locale on Lui propose de 

- choisir le chemin de son modèle 

- utiliser ollama 

- l'étape suivante c'est si oui ou non il veut stocker les vidéos en local 

- si oui il choisit la location 

- oui ou non il veut garder les fichiers temp 

- on lui demande le chemin d'accès du dossier avec les fichiers vidéo qu'on pourra mettre au hasard en boucle) (d'ailleurs j'ai oublié de le préciser on devra mettre les vidéos aléatoire et les photos aléatoire de tel sorte que ça face le même temps que l'audio. Et si il n'y a pas assez de vidéo on répète certaines deux fois où trois fois pour que ça suffisent)

- (ici ça va dépendre des recherches que je t'ai dit de faire plus haut à propos de prendre les vidéos en ligne)

- ici on demandera si il veut utiliser un modèle de génération d'images pour les illustrations dans les vidéos (par API, localement, pas du tout)

- si il choisit par API, il choisit le provider ensuite le modèle comme on a fait plus haut 

- si il choisit localement même chose (je veux que tu cherches sur internet pour voir comment on peut setup ça, concentre toi sur le model Z-image avec un lora pour speed un le temps de génération en diminuant le nombre de step)

- on utilisera aussi ce modèle pour les miniatures si nécessaire 

- ensuite on lui affichera le prompt que on utilisera pour la génération de text (celui qui est général et celui qui est particulier pour un titre de vidéo) et il aura l'option de modifier l'un ou l'autre ou de juste les laisser comme tel

- on fait la même chose pour tout les autres prompt

- ensuite on lui demandera de donner ses api on le JSON provide par Google pour poster les vidéos 

- ensuite on lui montrera tout ses choix, avec la possibilité de revenir sur une décision précise 

- (Donne moi le déroulement du setup complet avec les parties qu le j'aurais potentiellement oublié)


Maintenant lorsqu'il voudra génère une vidéo il pourra juste taper une commande dans son terminal (dit moi ce que fera la commande par défaut et tout les points de flexibilité qu'il pourrait donner a la commande)


Enfin l'orqu'il va lancer la commande le TUI va apparaître et va lui montrer une barre de progression en bas de l'écran du terminal ce qui ce passe a gauche (par exemple toutes les étapes sont affichés, l'étape courante est highlighted et on peut voir sa description et a droite les détails de l'étape courante (uniquement sont affichés) (et on peut scroller sur ce panel droit.
