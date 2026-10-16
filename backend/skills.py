"""Small, auditable alias catalog; not an ESCO or semantic competency assessment."""
import re

# name: aliases, category, foundational anchor, short exercise
CATALOG = {
 'Python': (['python'], 'Tooling modernization', 'programming', 'Rewrite one existing function in Python and test three boundary inputs.'),
 'Java': (['java'], 'Tooling modernization', 'object oriented', 'Implement one existing class in Java and verify its behavior with assertions.'),
 'JavaScript': (['javascript', 'ecmascript'], 'Tooling modernization', 'web', 'Add form validation to an existing web lab and test valid and invalid input.'),
 'TypeScript': (['typescript'], 'Tooling modernization', 'web', 'Add explicit types to one existing JavaScript module and fix compiler errors.'),
 'C++': (['c++', 'cpp'], 'Tooling modernization', 'programming', 'Compile one existing algorithm with a current compiler and add boundary assertions.'),
 'SQL': (['sql', 'structured query language'], 'Tooling modernization', 'database', 'Write a join and transaction for the current database assignment; test rollback.'),
 'PostgreSQL': (['postgresql', 'postgres'], 'Tooling modernization', 'database', 'Run existing SQL queries in PostgreSQL and compare query plans before and after an index.'),
 'MySQL': (['mysql'], 'Tooling modernization', 'database', 'Run the current database lab in MySQL and verify constraints with invalid inserts.'),
 'MongoDB': (['mongodb', 'mongo db'], 'Architectural shift', 'database', 'Model one existing dataset as documents and compare one query with the relational version.'),
 'Git': (['git', 'version control', 'github', 'gitlab'], 'Engineering workflow', 'programming', 'Commit the current assignment on a branch, open a pull request, and resolve one review comment.'),
 'Linux': (['linux', 'unix', 'bash', 'shell scripting'], 'Engineering workflow', 'operating system', 'Run the existing program from a shell script and capture its exit status and output.'),
 'Docker': (['docker', 'containerization', 'containerisation'], 'Engineering workflow', 'operating system', 'Package the existing lab in a Dockerfile and demonstrate the same output in a container.'),
 'CI/CD': (['ci/cd', 'continuous integration', 'github actions', 'jenkins'], 'Engineering workflow', 'software engineering', 'Add a GitHub Actions workflow that runs the existing tests on each pull request.'),
 'Automated testing': (['unit testing', 'unit tests', 'pytest', 'junit', 'jest', 'automated testing'], 'Industry blindspot', 'software engineering', 'Write three automated tests for the current function: normal, empty, and invalid input.'),
 'REST APIs': (['rest api', 'restful', 'rest apis', 'restful api'], 'Architectural shift', 'web', 'Expose one existing function as a REST endpoint and verify success and invalid-input responses.'),
 'React': (['react', 'reactjs', 'react.js'], 'Tooling modernization', 'web', 'Replace one static page component with React state and demonstrate an accessible input interaction.'),
 'Node.js': (['node.js', 'nodejs', 'node js'], 'Tooling modernization', 'web', 'Expose existing assignment logic through one Node.js route and verify two inputs.'),
 'Spring Boot': (['spring boot', 'springboot'], 'Tooling modernization', 'object oriented', 'Wrap an existing Java class in one Spring Boot endpoint and test its response.'),
 'FastAPI': (['fastapi', 'fast api'], 'Tooling modernization', 'programming', 'Expose the current Python function with FastAPI and add input validation and one test.'),
 'Django': (['django'], 'Tooling modernization', 'web', 'Map one existing data entity to a Django model and test one create/read operation.'),
 'AWS': (['aws', 'amazon web services'], 'Tooling modernization', 'network', 'Draw a deployment of the existing lab on AWS and explain permissions and cost limits; no paid deployment needed.'),
 'Azure': (['azure'], 'Tooling modernization', 'network', 'Map the existing lab to Azure compute and storage and document permissions; no paid deployment needed.'),
 'Pandas': (['pandas'], 'Tooling modernization', 'data', 'Clean an existing lab dataset with Pandas and assert missing-value and row-count expectations.'),
 'NumPy': (['numpy'], 'Tooling modernization', 'mathematics', 'Vectorize one existing numerical calculation with NumPy and verify equivalence.'),
 'PyTorch': (['pytorch'], 'Tooling modernization', 'machine learning', 'Run an instructor-provided tiny PyTorch model on an existing dataset and compare its loss across two runs.'),
 'TensorFlow': (['tensorflow'], 'Tooling modernization', 'machine learning', 'Run an instructor-provided small TensorFlow model and record training and validation metrics.'),
 'Scikit-learn': (['scikit-learn', 'sklearn', 'scikit learn'], 'Tooling modernization', 'machine learning', 'Train a baseline on the current dataset with a held-out split and report one appropriate metric.'),
 'Kubernetes': (['kubernetes', 'k8s'], 'Engineering workflow', 'distributed', 'Inspect an instructor-provided deployment manifest and explain replicas and health checks.'),
 'Terraform': (['terraform'], 'Engineering workflow', 'network', 'Read an instructor-provided infrastructure plan and identify resources and access boundaries.'),
 'Redis': (['redis'], 'Architectural shift', 'database', 'Add a small cache to a prepared database lab and demonstrate cache invalidation.'),
 'HTML/CSS': (['html', 'css', 'html5', 'css3'], 'Tooling modernization', 'web', 'Make one existing page responsive and verify its form has visible labels and keyboard focus.'),
}
THEORY = {'database': ['database', 'dbms', 'rdbms', 'relational algebra', 'normalization', 'acid'],
 'programming': ['programming', 'algorithm', 'data structures'],
 'object oriented': ['object oriented', 'object-oriented', 'inheritance', 'polymorphism'],
 'web': ['web', 'http', 'html', 'javascript'],
 'operating system': ['operating system', 'process scheduling', 'deadlock'],
 'software engineering': ['software engineering', 'software testing', 'software development'],
 'network': ['network', 'tcp', 'socket'], 'data': ['data analysis', 'data science', 'statistics'],
 'mathematics': ['mathematics', 'linear algebra', 'numerical'],
 'machine learning': ['machine learning', 'neural network'], 'distributed': ['distributed system']}
LEGACY = {'Turbo C': ['turbo c', 'turbo c++'], 'Oracle 9i': ['oracle 9i'],
 'Oracle 8i': ['oracle 8i'], 'Flash MX': ['flash mx'], 'Python 2': ['python 2.7', 'python 2'],
 'PHP 4': ['php 4']}
ADVANCED = {'Kubernetes', 'Terraform', 'PyTorch', 'TensorFlow', 'Redis'}

def pattern(alias):
    return re.compile(r'(?<![\w+#])' + re.escape(alias) + r'(?![\w+#])', re.I)

def evidence(text, aliases):
    for alias in aliases:
        match = pattern(alias).search(text)
        if match:
            return text[max(0, match.start()-90):min(len(text), match.end()+150)].strip()
    return None

def skills(text):
    return {name for name, spec in CATALOG.items() if evidence(text, spec[0])}
